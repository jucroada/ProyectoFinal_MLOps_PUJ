--  crear base de datos de mlflow para la metadata
CREATE DATABASE mlflow;
GRANT PRIVILEGES ON DATABASE mlflow TO airflow;

--  crear esquemas para los conjuntos de datos en limpio y crudos
CREATE SCHEMA IF NOT EXISTS raw_data;
GRANT USAGE ON SCHEMA raw_data TO airflow;

CREATE SCHEMA IF NOT EXISTS clean_data;
GRANT USAGE ON SCHEMA clean_data TO airflow;

