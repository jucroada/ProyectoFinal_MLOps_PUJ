FROM python:3.9

# Argumentos para MinIO/MLflow
ARG MLFLOW_S3_ENDPOINT_URL=http://minio:9000
ARG AWS_ACCESS_KEY_ID=admin
ARG AWS_SECRET_ACCESS_KEY=supersecret

# Variables de entorno para que estén disponibles dentro del contenedor
ENV MLFLOW_S3_ENDPOINT_URL=${MLFLOW_S3_ENDPOINT_URL}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

# Crear directorio de trabajo
RUN mkdir /work
WORKDIR /work

# Copiar archivos del contexto de construcción
COPY . .

# Instalar Jupyter y JupyterLab
RUN pip install jupyter==1.0.0 -U && \
    pip install jupyterlab==3.6.1

# Instalar dependencias básicas para pruebas con DAGs, MLflow, etc.
RUN pip install --no-cache-dir \
    apache-airflow==2.7.1 \
    mlflow \
    boto3 \
    pandas \
    scikit-learn \
    ipykernel \
    matplotlib \
    seaborn

# Exponer puerto JupyterLab
EXPOSE 8888

# Comando de entrada
ENTRYPOINT ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--NotebookApp.token=''"]