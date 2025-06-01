import os
import json
import pandas as pd
import mlflow
import uvicorn
import requests
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, text
from mlflow.tracking import MlflowClient
from pydantic import BaseModel
from typing import Dict, Any, List

from fastapi.middleware.cors import CORSMiddleware

from .models import PredictRequest, PredictResponse, ModelUpdatePayload, HistoryEntry, ShapResponse

app = FastAPI()

# Permitir CORS si es necesario
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variables de entorno obligatorias
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
CLEAN_DB_URI = os.getenv("CLEAN_DB_CONN")        
RAW_DB_URI   = os.getenv("RAW_DB_CONN")        
MODEL_NAME   = "my_model"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
client = MlflowClient()

# Globals para cachear modelo en memoria
model_in_memory = None
active_run_id    = None
active_version   = None
active_features = None  # lista de columnas esperadas por el modelo activo

def load_production_model():
    global model_in_memory, active_run_id, active_version, active_features
    prod = client.get_latest_versions(MODEL_NAME, stages=["Production"])
    if not prod:
        raise RuntimeError("No se encontró modelo en Production")
    info = prod[0]
    run_id = info.run_id
    version = int(info.version)
    if model_in_memory is not None and run_id == active_run_id:
        return

    model_uri = f"runs:/{run_id}/model"
    model_in_memory = mlflow.sklearn.load_model(model_uri)
    active_run_id  = run_id
    active_version = version

    # Descargar features esperadas
    try:
        features_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="features/final_features.json")
        with open(features_path, "r") as f:
            active_features = json.load(f)
        print(f"[FastAPI] final_features.json cargadas: {active_features}")
    except Exception as e:
        print(f"[FastAPI] No se pudo cargar final_features.json para el modelo, error: {e}")
        active_features = None

def clean_input_features(raw_features: dict) -> dict:
    cleaned = raw_features.copy()
    for c in ["street", "city", "state", "status"]:
        if c in cleaned and cleaned[c] is not None:
            cleaned[c] = str(cleaned[c]).strip().lower()
    if "zip_code" in cleaned and cleaned["zip_code"] is not None:
        import re
        cleaned["zip_code"] = re.sub(r"\D+", "", str(cleaned["zip_code"]))
    return cleaned


# Al arrancar la app, cargamos el modelo
@app.on_event("startup")
def startup_event():
    try:
        load_production_model()
    except Exception as e:
        print(f"[FastAPI] Advertencia: no se pudo cargar Production al iniciar: {e}")

@app.post("/hooks/model_update", summary="Hook para recargar el modelo en producción")
def hook_model_update(payload: ModelUpdatePayload):
    """
    Endpoint que Airflow llamará (POST) cuando detecte un nuevo modelo en Production.
    Payload: {"model_name": "...", "model_version": X, "run_id": "..."}
    """
    print(f"[FastAPI] /hooks/model_update llamado con: {payload.dict()}")
    # Validar que sea el mismo nombre de modelo esperado
    if payload.model_name != MODEL_NAME:
        print(f"[FastAPI] ERROR: Nombre de modelo inesperado: {payload.model_name}")
        raise HTTPException(status_code=400, detail="Nombre de modelo inesperado")

    try:
        # Forzar recarga del modelo siempre (aunque sea la misma versión)
        load_production_model()
        print(f"[FastAPI] Modelo recargado en memoria: run_id={active_run_id}, version={active_version}")
        return { "status": "reloaded", "run_id": active_run_id, "version": active_version }
    except Exception as e:
        print(f"[FastAPI] ERROR al recargar modelo: {e}")
        raise HTTPException(status_code=500, detail=f"Error cargando modelo: {e}")


@app.post("/predict", response_model=PredictResponse, summary="Hacer inferencia con el modelo en Production")
def predict(request: PredictRequest):
    try:
        load_production_model()
    except Exception as e:
        print(f"[FastAPI] ERROR: Modelo no disponible en memoria: {e}")
        raise HTTPException(status_code=500, detail=f"Modelo no disponible: {e}")

    # Aplica el preprocesamiento mínimo igual al pipeline de limpieza
    input_clean = clean_input_features(request.features)
    input_df = pd.DataFrame([input_clean])

    if active_features:
        input_df = input_df.reindex(columns=active_features, fill_value=None)

    try:
        pred = model_in_memory.predict(input_df)
    except Exception as e:
        print(f"[FastAPI] ERROR en predict: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Error en predict: {e}. Revisa que los features coincidan con los usados en el modelo."
        )

    response = PredictResponse(
        prediction=float(pred[0]),
        run_id=active_run_id,
        model_version=active_version
    )

    # Guarda el input original
    try:
        engine = create_engine(RAW_DB_URI)
        with engine.begin() as conn:
            conn.execute(text(f"""
                INSERT INTO raw_data.inference_logs (
                    model_name, model_version, run_id, input_data, prediction
                ) VALUES (
                    :mname, :mver, :run, :input, :pred
                )
            """), {
                "mname": MODEL_NAME,
                "mver":  active_version,
                "run":   active_run_id,
                "input": json.dumps(request.features),  # Guarda el input crudo
                "pred":  json.dumps({"prediction": float(pred[0])})
            })
    except Exception as e:
        print(f"[FastAPI] ERROR al guardar el log de inferencia: {e}")

    return response

@app.get("/history", response_model=List[HistoryEntry], summary="Obtener historial de modelos entrenados")
def get_history():
    """
    - Consulta toda la tabla clean_data.model_history y devuelve la lista 
      de registros (experiment_id, run_id, metrics, promoted, shap_uri, trained_at).
    """
    engine = create_engine(CLEAN_DB_URI)
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT experiment_id, run_id, model_version, new_mse, new_rmse, new_mae, new_r2, prod_mse, prod_rmse, prod_mae, prod_r2, promoted, shap_uri, trained_at FROM clean_data.model_history ORDER BY trained_at DESC;"))
        rows = result.fetchall()

    history_list = []
    for r in rows:
        # r: (experiment_id, run_id, model_version, new_mse, new_rmse, new_mae, new_r2, prod_mse, prod_rmse, prod_mae, prod_r2, promoted, shap_uri, trained_at)
        history_list.append(HistoryEntry(
            experiment_id=r[0],
            run_id=r[1],
            model_version=r[2],
            new_mse=r[3],
            new_rmse=r[4],
            new_mae=r[5],
            new_r2=r[6],
            prod_mse=r[7],
            prod_rmse=r[8],
            prod_mae=r[9],
            prod_r2=r[10],
            promoted=r[11],
            shap_uri=r[12],
            trained_at=r[13].isoformat()
        ))
    return history_list

@app.get("/shap/{run_id}", response_model=ShapResponse, summary="Descargar SHAP values para un run_id")
def get_shap(run_id: str):
    """
    - Input: run_id correspondiente a un registro en MLflow.
    - El artifact 'shap_values/shap_values.parquet' debe existir en MLflow (S3/MinIO).
    - Descarga vía mlflow.artifacts.download_artifacts y lee el parquet.
    - Devuelve un JSON con {run_id, shap_values: {feature1:[…], feature2:[…],…}}.
    """
    # Construir path lógico para el artifact
    try:
        # Descarga localmente (retorna path al directorio temporal donde se ubicó shap_values.parquet)
        local_path = mlflow.artifacts.download_artifacts(run_id=run_id, artifact_path="shap_values/shap_values.parquet")
        # Leer parquet
        shap_df = pd.read_parquet(local_path)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"No se encontró SHAP para {run_id}: {e}")

    # Convertir DataFrame a dict of lists
    shap_dict = { col: shap_df[col].tolist() for col in shap_df.columns }
    return ShapResponse(run_id=run_id, shap_values=shap_dict)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8989)
