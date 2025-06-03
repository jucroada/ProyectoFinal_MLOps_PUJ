# Despliegue de MLOps en Kubernetes - Guía Completa

Este documento proporciona instrucciones paso a paso para desplegar la plataforma MLOps completa en Kubernetes, incorporando todas las correcciones y mejoras realizadas durante el desarrollo.

## Componentes

- **PostgreSQL**: Base de datos para Airflow y MLflow
- **Redis**: Broker para Airflow Celery Executor
- **Airflow**: Orquestador de flujos de trabajo
- **MinIO**: Almacenamiento de objetos compatible con S3
- **MLflow**: Plataforma para gestión del ciclo de vida de ML
- **FastAPI**: API para servir modelos de ML
- **Streamlit**: Interfaz de usuario
- **Prometheus**: Monitoreo de métricas
- **Grafana**: Visualización de métricas

## Requisitos previos

- Kubernetes cluster (Minikube, K3s, EKS, AKS, GKE, etc.)
- kubectl configurado para acceder al cluster

## Pasos para el despliegue

### 1. Crear secretos

```bash
kubectl apply -f secrets/minio-secrets.yaml
```

### 2. Configurar almacenamiento persistente para PostgreSQL

```bash
kubectl apply -f postgres/postgres-pv-pvc.yaml
```

### 3. Desplegar PostgreSQL

```bash
kubectl apply -f postgres/postgres-deployment.yaml
```

### 4. Desplegar Redis

```bash
kubectl apply -f airflow/redis-deployment.yaml
```

### 5. Desplegar MinIO

```bash
kubectl apply -f minio/minio-deployment.yaml
kubectl apply -f minio/minio-service.yaml
```

### 6. Desplegar MLflow con inicialización de base de datos

```bash
kubectl apply -f mlflow/mlflow-fix.yaml
kubectl apply -f mlflow/mlflow-service.yaml
```

### 7. Desplegar Airflow con DAGs y logs compartidos

```bash
# Crear volumen persistente para logs
kubectl apply -f airflow/airflow-logs-pv.yaml

# Aplicar ConfigMap para configuración
kubectl apply -f airflow/airflow-configmap.yaml

# Aplicar ConfigMaps para DAGs
kubectl apply -f airflow/airflow-dags-configmap-1.yaml
kubectl apply -f airflow/airflow-dags-configmap-2.yaml
kubectl apply -f airflow/airflow-dags-configmap-3.yaml

# Desplegar Airflow con todos los componentes y volumen compartido para logs
kubectl apply -f airflow/airflow-unified.yaml

# Verificar que los pods están en ejecución
kubectl get pods -l 'app in (airflow-webserver,airflow-scheduler,airflow-worker,airflow-triggerer)'
```

### 8. Desplegar FastAPI con soporte para métricas

```bash
kubectl apply -f fastapi/fastapi-deployment.yaml
kubectl apply -f fastapi/fastapi-service.yaml
```

### 9. Desplegar Prometheus y Grafana

```bash
# Prometheus
kubectl apply -f prometheus/prometheus-configmap.yaml
kubectl apply -f prometheus/prometheus-deployment.yaml

# Grafana
kubectl apply -f grafana/grafana-dashboards-configmap.yaml
kubectl apply -f grafana/grafana-dashboard-configmap.yaml
kubectl apply -f grafana/grafana-datasource-configmap.yaml
kubectl apply -f grafana/grafana-deployment.yaml
```

### 10. Desplegar Streamlit

```bash
kubectl apply -f streamlit/streamlit-deployment.yaml
kubectl apply -f streamlit/streamlit-service.yaml
```

## Acceso a los servicios

Para acceder a los servicios desde fuera del cluster, puedes usar port-forwarding:

se puede utilizar host.docker.internal para acceder localmente, pero no es recomendable, necesitamos actividad en servidor, por ende hay dos opciones, dejamos por forward de airflow cuando necesite consumo de datos del profe, o hacer un node port o external port api para que se pueda acceder de manera alterna 

```bash
# Airflow UI
kubectl port-forward svc/airflow-webserver 8080:8080

# MLflow UI
kubectl port-forward svc/mlflow 5000:5000

# MinIO Console
kubectl port-forward svc/minio 9001:9001

# FastAPI
kubectl port-forward svc/fastapi 8989:8989

# Streamlit
kubectl port-forward svc/streamlit 8501:8501

# Grafana
kubectl port-forward svc/grafana 3000:3000

# Prometheus
kubectl port-forward svc/prometheus 9090:9090
```

## Verificación del despliegue

```bash
# Verificar que todos los pods estén en estado "Running"
kubectl get pods

# Verificar los servicios
kubectl get services
```

## Solución de problemas comunes

### 1. Problema: Logs no visibles en Airflow

**Solución**: Hemos implementado un volumen compartido para los logs entre todos los componentes de Airflow. Si sigues sin poder ver los logs:

```bash
# Verificar que el volumen de logs está correctamente montado
kubectl exec -it deployment/airflow-webserver -- ls -la /opt/airflow/logs

# Verificar permisos en el directorio de logs
kubectl exec -it deployment/airflow-webserver -- chmod -R 777 /opt/airflow/logs
```

### 2. Problema: DAGs no visibles en Airflow

**Solución**: Asegúrate de que los ConfigMaps de DAGs están correctamente aplicados y montados:

```bash
# Verificar que los ConfigMaps existen
kubectl get configmaps | grep airflow-dags

# Verificar que los DAGs están correctamente montados
kubectl exec -it deployment/airflow-webserver -- ls -la /opt/airflow/dags
```

Si los DAGs no aparecen, reinicia el webserver:

```bash
kubectl rollout restart deployment/airflow-webserver
```

### 3. Problema: Tareas en estado "queued" en Airflow

**Solución**: Verifica que el worker de Airflow está funcionando correctamente:

```bash
# Verificar el estado del worker
kubectl get pods -l app=airflow-worker

# Verificar los logs del worker
kubectl logs -l app=airflow-worker
```

Si el worker está en CrashLoopBackOff, verifica que:
- El directorio temporal existe: `/opt/airflow/dags/tmp`
- Las variables de entorno están correctamente configuradas
- Redis está funcionando correctamente

### 4. Problema: Conectividad entre Airflow y MLflow

Si Airflow no puede conectarse a MLflow, verifica:

```bash
# Verificar que el servicio de MLflow está funcionando
kubectl get svc mlflow

# Verificar que el pod de MLflow está en estado Running
kubectl get pods -l app=mlflow

# Probar la conectividad desde el pod de Airflow
kubectl exec -it deployment/airflow-worker -- curl -v mlflow:5000
```

Si persisten los problemas, reinicia los pods:

```bash
kubectl rollout restart deployment/mlflow
kubectl rollout restart deployment/airflow-worker
kubectl rollout restart deployment/airflow-scheduler
```

### 5. Problema: Métricas no visibles en Grafana

Si Grafana no muestra las métricas de FastAPI:

```bash
# Verificar que FastAPI está exponiendo métricas
kubectl exec -it deployment/fastapi -- curl localhost:8989/metrics

# Verificar que Prometheus está recolectando métricas
kubectl port-forward svc/prometheus 9090:9090
# Luego abre http://localhost:9090 y busca métricas como predict_requests_total

# Verificar que Grafana está configurado correctamente
kubectl port-forward svc/grafana 3000:3000
# Luego abre http://localhost:3000 y verifica las fuentes de datos
```

### 6. Problema: Pods en estado "Pending" o "ImagePullBackOff"

**Solución**: Verifica si hay suficientes recursos en el cluster o problemas con las imágenes:

```bash
# Ver detalles del pod
kubectl describe pod <nombre-del-pod>

# Ver eventos del cluster
kubectl get events --sort-by='.metadata.creationTimestamp'
```

Para problemas con MLflow específicamente, hemos aumentado los recursos:

```bash
# Verificar los recursos asignados a MLflow
kubectl describe pod -l app=mlflow
```

## Notas importantes

- **Credenciales por defecto**:
  - Airflow: usuario=airflow, contraseña=airflow
  - MinIO: usuario=admin, contraseña=supersecret
  - Grafana: usuario=admin, contraseña=admin

- **Volúmenes**:
  - El volumen para los logs de Airflow está configurado como PersistentVolume con hostPath en `/tmp/airflow-logs`
  - Los volúmenes para DAGs y plugins están configurados como emptyDir
  - El directorio temporal `/opt/airflow/dags/tmp` es necesario para algunos DAGs

- **Configuraciones especiales**:
  - MLflow tiene configurado readiness y liveness probes para garantizar su disponibilidad
  - FastAPI tiene anotaciones para que Prometheus pueda descubrir automáticamente el pod
  - Grafana está configurado con Prometheus como fuente de datos predeterminada

## Limpieza

Para eliminar todos los recursos creados:

```bash
kubectl delete -f streamlit/
kubectl delete -f grafana/
kubectl delete -f prometheus/
kubectl delete -f fastapi/
kubectl delete -f airflow/airflow-unified.yaml
kubectl delete -f airflow/airflow-dags-configmap-3.yaml
kubectl delete -f airflow/airflow-dags-configmap-2.yaml
kubectl delete -f airflow/airflow-dags-configmap-1.yaml
kubectl delete -f airflow/airflow-configmap.yaml
kubectl delete -f airflow/redis-deployment.yaml
kubectl delete -f mlflow/
kubectl delete -f minio/
kubectl delete -f postgres/
kubectl delete -f secrets/
kubectl delete pv airflow-logs-pv
```

```bash
# 1. Eliminar todos los deployments y servicios de Airflow
kubectl delete -f airflow/airflow-unified.yaml
kubectl delete -f airflow/airflow-logs-pv.yaml
kubectl delete -f airflow/airflow-dags-configmap-3.yaml
kubectl delete -f airflow/airflow-dags-configmap-2.yaml
kubectl delete -f airflow/airflow-dags-configmap-1.yaml
kubectl delete -f airflow/airflow-configmap.yaml
kubectl delete -f airflow/redis-deployment.yaml

# 2. Eliminar PersistentVolumeClaim y PersistentVolume
kubectl delete pvc airflow-logs-pvc
kubectl delete pv airflow-logs-pv

# 3. Eliminar cualquier ConfigMap restante relacionado con Airflow
kubectl delete configmap airflow-config
kubectl delete configmap airflow-dags-1
kubectl delete configmap airflow-dags-2
kubectl delete configmap airflow-dags-3

# 4. Eliminar la base de datos de Airflow en PostgreSQL
# Primero, conectarse al pod de PostgreSQL
kubectl exec -it deployment/mlops-postgres -- psql -U airflow -d postgres

# Dentro de PostgreSQL, ejecutar:
# DROP DATABASE airflow;
# CREATE DATABASE airflow;
# \q

# 5. Verificar que no queden recursos de Airflow
kubectl get all 
kubectl get configmap 
kubectl get pv,pvc 

```