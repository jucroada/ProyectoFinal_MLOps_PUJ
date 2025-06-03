import os
import json
import pandas as pd
import mlflow
import uvicorn
import requests
from fastapi import FastAPI, HTTPException, Depends, Body
from fastapi.responses import Response
from sqlalchemy import create_engine, text
from mlflow.tracking import MlflowClient
from pydantic import BaseModel
from typing import Dict, Any, List
import time

from fastapi.middleware.cors import CORSMiddleware

from prometheus_client import (
    Counter, generate_latest, CONTENT_TYPE_LATEST,
    Summary, Gauge
)

from .models import PredictRequest, PredictResponse, ModelUpdatePayload, HistoryEntry, ShapResponse


app = FastAPI(
    title="API de Predicción de especie de Precio de Vivienda",
    description="Predice el valor de una vivienda según características, además de entregar historicos de modelos y SHAP values.",
    version="1.0.0"
)
# Métricas de Prometheus
PREDICTION_COUNTER = Counter("predict_requests_total", "Número de predicciones realizadas")
PREDICTION_LATENCY = Summary("predict_latency_seconds", "Latencia del endpoint /predict (segundos)")
UPTIME = Gauge("api_uptime", "API activa (1 si está corriendo)")

# Activamos la métrica de uptime en tiempo de carga
UPTIME.set(1)


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

def clean_float(val):
    import math
    if val is None:
        return None
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    return val


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
    PREDICTION_COUNTER.inc()
    start_time = time.time()
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
    latency = time.time() - start_time
    PREDICTION_LATENCY.observe(latency)
    return response

@app.get("/history", response_model=List[HistoryEntry], summary="Obtener historial de modelos entrenados")
async def get_history():
    """
    - Consulta toda la tabla clean_data.model_history y devuelve la lista 
      de registros (experiment_id, run_id, run_name, metrics, promoted, shap_uri, trained_at).
    """
    engine = create_engine(CLEAN_DB_URI)
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT experiment_id, model_name, run_id, run_name, model_version, new_mse, new_rmse, new_mae, new_r2, prod_mse, prod_rmse, prod_mae, prod_r2, promoted, shap_uri, trained_at FROM clean_data.model_history ORDER BY trained_at DESC;"
        ))
        rows = result.fetchall()

    history_list = []
    for r in rows:
        history_list.append(HistoryEntry(
            experiment_id=r[0],
            model_name=r[1],
            run_id=r[2],
            run_name=r[3],
            model_version=r[4],
            new_mse=clean_float(r[5]),
            new_rmse=clean_float(r[6]),
            new_mae=clean_float(r[7]),
            new_r2=clean_float(r[8]),
            prod_mse=clean_float(r[9]),
            prod_rmse=clean_float(r[10]),
            prod_mae=clean_float(r[11]),
            prod_r2=clean_float(r[12]),
            promoted=r[13],
            shap_uri=r[14],
            trained_at=r[15].isoformat()
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

@app.post("/predict_shap", summary="Inferencia y SHAP para una muestra")
def predict_shap(request: PredictRequest = Body(...)):
    try:
        load_production_model()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Modelo no disponible: {e}")

    # Preprocesa la entrada como en predict
    input_clean = clean_input_features(request.features)
    input_df = pd.DataFrame([input_clean])
    if active_features:
        input_df = input_df.reindex(columns=active_features, fill_value=None)

    # Predicción
    try:
        pred = model_in_memory.predict(input_df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en predict: {e}")

    # SHAP para la observación individual
    try:
        # Cargar preprocesador y modelo interno
        preproc = model_in_memory.named_steps["preproc"]
        reg = model_in_memory.named_steps["reg"]
        input_trans = preproc.transform(input_df)
        explainer = shap.LinearExplainer(reg, input_trans, feature_perturbation="interventional")
        shap_values = explainer.shap_values(input_trans)
        cols = preproc.get_feature_names_out()
        # shap_values es shape (1, n_features)
        shap_dict = {col: float(val) for col, val in zip(cols, shap_values[0])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando SHAP: {e}")

    return {
        "prediction": float(pred[0]),
        "shap_values": shap_dict,
        "run_id": active_run_id,
        "model_version": active_version
    }

@app.get("/health")
def health():
    return {"status": "ok"}

# Endpoint de métricas
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8989)
