import os
from datetime import datetime, timedelta

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor

import mlflow
from mlflow.tracking import MlflowClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
import shap
from sqlalchemy import create_engine, text

RAW_DB_URI   = os.getenv("RAW_DB_CONN")
CLEAN_DB_URI = os.getenv("CLEAN_DB_CONN")
SCHEMA_CLEAN   = "clean_data"
TABLE_CLEAN    = "clean_data_init"
EXPERIMENT_NAME = "modeling_pipeline"

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="modeling_pipeline",
    default_args=default_args,
    start_date=datetime(2025, 5, 1),
    schedule_interval=None,    # arranca por sensor o trigger
    catchup=False,
    tags=["modeling","mlflow"],
) as dag:

    # 1) Espera a que clean data esté lista
    wait_for_clean = ExternalTaskSensor(
        task_id="wait_for_clean_data",
        external_dag_id="data_pipeline",
        external_task_id="transform_and_load_clean",
        mode="reschedule",
        poke_interval=60,
        timeout=60*60,
    )

    # 2) Carga clean_data y separa train/test
    def extract_data():
        engine = create_engine(CLEAN_DB_URI)
        df = pd.read_sql_table(TABLE_CLEAN, schema=SCHEMA_CLEAN, con=engine)
        # Asumiendo que 'split' ya existe
        df_train = df[df.split=="train"].drop(columns=["split"])
        df_test  = df[df.split=="test"].drop(columns=["split"])
        # Serializa a CSV temp o XCom
        df_train.to_parquet("/tmp/train.parquet", index=False)
        df_test.to_parquet("/tmp/test.parquet", index=False)

    extract = PythonOperator(
        task_id="extract_train_test",
        python_callable=extract_data,
    )

    # 3) Entrena y registra experimento en MLflow
    def train_and_log():
        mlflow.set_experiment(EXPERIMENT_NAME)
        with mlflow.start_run() as run:
            df_train = pd.read_parquet("/tmp/train.parquet")
            X = df_train.drop(columns=["target"])      # ajusta según tu label
            y = df_train["target"]
            model = RandomForestClassifier(n_estimators=50, random_state=42)
            model.fit(X, y)

            # guarda modelo
            mlflow.sklearn.log_model(model, "model", registered_model_name="my_model")
            # métricas
            df_test = pd.read_parquet("/tmp/test.parquet")
            y_pred = model.predict_proba(df_test.drop(columns=["target"]))[:,1]
            auc = roc_auc_score(df_test["target"], y_pred)
            mlflow.log_metric("roc_auc", auc)

    train = PythonOperator(
        task_id="train_model",
        python_callable=train_and_log,
    )

    # 4) Evalúa vs producción y promueve si mejora
    def compare_and_promote():
        client = MlflowClient()
        # run actual
        exp = client.get_experiment_by_name(EXPERIMENT_NAME)
        runs = client.search_runs([exp.experiment_id], order_by=["attributes.start_time desc"], max_results=1)
        new_run = runs[0]
        new_auc = new_run.data.metrics["roc_auc"]

        # coger prod
        prod_versions = client.get_latest_versions(name="my_model", stages=["Production"])
        if prod_versions:
            prod_uri = prod_versions[0].source
            prod_model = mlflow.sklearn.load_model(prod_uri)
            df_test = pd.read_parquet("/tmp/test.parquet")
            y_pred = prod_model.predict_proba(df_test.drop(columns=["target"]))[:,1]
            prod_auc = roc_auc_score(df_test["target"], y_pred)
        else:
            prod_auc = 0.0

        # si mejora, promueve
        if new_auc > prod_auc:
            client.transition_model_version_stage(
                name="my_model",
                version=int(new_run.data.tags["mlflow.modelVersion"]),
                stage="Production"
            )

        # guarda historico en BD
        engine = create_engine(RAW_DB_URI)  # o CLEAN_DB_URI
        engine.execute(text("""
            INSERT INTO model_history(run_id, new_auc, prod_auc, promoted, ts)
            VALUES (:rid, :na, :pa, :pr, now())
        """), {
            "rid": new_run.info.run_id,
            "na": new_auc,
            "pa": prod_auc,
            "pr": new_auc>prod_auc
        })

    evaluate = PythonOperator(
        task_id="compare_and_promote",
        python_callable=compare_and_promote,
        execution_timeout=timedelta(minutes=10),
    )

    # 5) Genera SHAP values y registra artefacto
    def compute_shap():
        mlflow.set_experiment(EXPERIMENT_NAME)
        client = MlflowClient()
        exp = client.get_experiment_by_name(EXPERIMENT_NAME)
        runs = client.search_runs([exp.experiment_id], order_by=["attributes.start_time desc"], max_results=1)
        run = runs[0]
        model_uri = f"runs:/{run.info.run_id}/model"
        model = mlflow.sklearn.load_model(model_uri)

        df_test = pd.read_parquet("/tmp/test.parquet")
        X_test = df_test.drop(columns=["target"])
        explainer = shap.Explainer(model, X_test)
        shap_vals = explainer(X_test)

        # guardar como artefacto (por simplicidad parquet)
        shap_df = pd.DataFrame(shap_vals.values, columns=X_test.columns)
        shap_df.to_parquet("/tmp/shap_values.parquet", index=False)
        mlflow.log_artifact("/tmp/shap_values.parquet", artifact_path="shap_values")

    shap_task = PythonOperator(
        task_id="compute_shap",
        python_callable=compute_shap,
        execution_timeout=timedelta(minutes=10),
    )

    wait_for_clean >> extract >> train >> evaluate >> shap_task
