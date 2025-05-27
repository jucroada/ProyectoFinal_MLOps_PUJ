#!/bin/sh
set -e

# arrancamos el servidor minio en background
minio server /data --console-address ":9001" &
MINIO_PID=$!

# esperamos a que minio responda y configuramos el alias 'local'
TRIES=0
until mc alias set local http://127.0.0.1:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"; do
  TRIES=$((TRIES+1))
  if [ "$TRIES" -gt 30 ]; then
    echo "ERROR: MinIO no responde en http://127.0.0.1:9000" >&2
    exit 1
  fi
  sleep 1
done

# creamos el bucket (si no existe, ignoramos el error)
mc mb local/mlflows3 || true

# dejamos minio en primer plano
wait $MINIO_PID
