FROM apache/airflow:2.6.0-python3.9

# Copiar el archivo requirements.txt a la raíz de la imagen
COPY requirements.txt /requirements.txt

# Instalar las dependencias listadas en el requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt