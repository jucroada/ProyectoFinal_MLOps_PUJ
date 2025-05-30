#!/bin/sh
set -e

# Iniciamos MinIO en background
minio server /data --console-address ":9001" &
MINIO_PID=$!

# Esperamos a que MinIO esté disponible
TRIES=0
MAX_TRIES=30
until mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -ge "$MAX_TRIES" ]; then
    echo "❌ ERROR: MinIO no respondió en http://127.0.0.1:9000 después de $MAX_TRIES intentos." >&2
    kill "$MINIO_PID"
    exit 1
  fi
  echo "⏳ Esperando que MinIO inicie (intento $TRIES)..."
  sleep 1
done

# Creamos bucket si no existe
mc mb local/mlflows3 || echo "Bucket ya existe o error ignorado"

# Ejecutamos el proceso en foreground
wait "$MINIO_PID"