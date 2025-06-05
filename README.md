#   Proyecto Final MLOps 

En este repositorio hacemos el proceso de desarrollo del proyecto, iniciando desarrollo por docker compose, luego deesto hacemos publicación de las imagenes, y actualizamos el docker compose apuntando a las imagenes publicadas en docker hub para verificar el desarrollo hecho hasta ese punto, luego, migramos todo a k8s, haciendo un manifiesto en general para cada uno de los microservicios que necesitamos para definir la arquitectura planteada en el docker compose y hacemos el despliegue verificando el correcto levantamiento y funcionamiento del flujo, tomamos en cuenta levantar postgres antes de airflow para evitar problemas de levantamiento de los microservicios de airflow. Luego, instalamos helm y por medio de este empezamos a hacer la integración de todos los servicios, hacemos la publicación o enrutamiento del chart a un repositorio de github para hacer su respectiva sincronización, levantamos todo el flujo, y verificamos su correcto levantamiento, por último, finalizamos con la configuración del archivo ci-cd.yml para la sincronización con el repositorio de github y la activación de actions, y por último la creación de argo-cd/app.yaml para su correspondiente estructuración.

Antes de empezar, entendemos como accedemos a la información de la api correspondiente

```bash
# comprobamos si obtenemos respuesta con la ip via pin 
ping 10.43.101.108
```
![Respuesta API Data](images/ping_apiData.png)

```bash 
#   Accedemos al puerta publicado para verificar conectividad a la API (endpoint raíz)
curl http://10.43.101.108:80
```
![Servicio de la API](images/APIresponse.png)

```bash
#   indagamos sobre el contenido de la api
curl http://10.43.101.108:80/openapi.json
```

/home/estudiante/Documents/ProyectoFinal_MLOps_PUJ

Rutas encontradas
/metrics con método GET usando Prometheus 
/health con método GET para verificar con status OK
/data con método GET con información necesaría `group_number` y `day`
/restart_data_generation con método GET con información necesaria `group_number` y `day`

Con lo que nuestras consultas a la api serán llevadas a cabo de los siguientes url

```plaintext
http://10.43.101.108:80/data?group_number=6&day=Wednesday  # solicitud de datos
http://10.43.101.108:80/restart_data_generation?group_number=6&day=Wednesday  # reinicio en el contador de solicitud a la API
```

Desarrollamos todo el proceso para que el proceso se pueda levantar de manera automatica a traves del uso de docker compose, como nuestra base de levantamiento inicial, ya con este medio construido por completo, se hace la migración a kubernetes a traves de helm, sincronizamos el proceso con github 

Para levantar La arquitectura por medio de docker utilizamos los siguientes comandos 

```bash
docker compose up airflow-init 
docker compose up --build -d 
```

Para bajar por completo la arquitectura levantada por medio de docker utilizamos el siguiente comando

```bash 
docker compose down -v --rmi all 
```

Para hacer seguimientos de las tablas y almacenamiento de la base de datos generada en postgres

```bash
docker compose exec mlops-postgres psql -U airflow -d airflow -c "\l"
docker compose exec mlops-postgres psql -U airflow -d airflow -c "\dt *.*"
```

```plaintext
http://localhost:8080      #   airflow
http://localhost:9001      #   minio
http://localhost:5000      #   mlflow
http://localhost:8888      # jupyterlab (este servicio lo borramos dado que sólo lo usamos apra pruebas)
http://localhost:8989      # punto de acceso a la API para consumo del modelo entrenado 
http://localhost:9090          # prometheus 
http://localhost:3000       # grafana 
```

anotación, para hacer tunel usando port forwarding a traves de la conexión ssh de la vm 


ejemplos de prueba para la api y consumo del modelo 

```plaintext 
{
  "features": {
    "brokered_by": 101,
    "status": "for sale",
    "bed": 3,
    "bath": 2,
    "acre_lot": 0.25,
    "street": "123 elm st",
    "city": "springfield",
    "state": "illinois",
    "zip_code": "62704",
    "house_size": 1500,
    "prev_sold_date": "2022-03-15"
  }
}
{
  "features": {
    "brokered_by": 55,
    "status": "for sale",
    "bed": 4,
    "bath": 3,
    "acre_lot": 0.4,
    "street": "456 oak ave",
    "city": "shelbyville",
    "state": "illinois",
    "zip_code": "62565",
    "house_size": 1800,
    "prev_sold_date": "2023-01-22"
  }
}
```

Publicación de las imagenes en docker hub de los servicios desarrollados 



Publicación de cada imagen 
En función decomandos bash, se construyen las imagenes base con las cuales se arranca cada servicio que es cargado a traves dedocker compose, por lo tanto cada una se crea de manera invidual siguiendo el esquema construcción -> publicación -> docker compose actualizado -> migración a manifiestos

```bash
docker build -t blutenherz/airflow-mlops:1.0.0 .
docker push blutenherz/airflow-mlops:1.0.0

docker build -t blutenherz/fastapi-mlops:1.0.0 .
docker push blutenherz/fastapi-mlops:1.0.0

docker build -t blutenherz/minio-mlops:1.0.0 .
docker push blutenherz/minio-mlops:1.0.0

docker build -t blutenherz/mlflow-mlops:1.0.0 .
docker push blutenherz/mlflow-mlops:1.0.0

docker build -t blutenherz/streamlit-mlops:1.0.0 .
docker push blutenherz/streamlit-mlops:1.0.0
```



## Migración a kubernetes 

El proceso de kubernetes nos dirigimos al directorio llamado como k8s, acá hacemos la construcción de todos los manifiestos necesarios con los microservicios correspondientes, usando imagenes personalizadas publicadas en docker hub como imagenes de libre acceso que no se necesito niguna personalización por nuestra parte. 


```bash
kubectl version --client 
```

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

##  Migración a Helm   

Este proceso se hace ya con los manifiestos desarrollados y probados para hacer el levantamiento del desarrollo del proyecto vía kubernetes, para este paso utilizamos helm chart para la configuración y levantamiento por este medio, el desarrollo de este proceso se hace dentro del directorio charts, de manera analoga como desarrollamos k8s.


# Documentación de Charts para MLOps

## 1. Migración de Manifiestos a Helm Charts

La transición de manifiestos de Kubernetes a Helm Charts se realizó siguiendo una estructura organizada y modular. A continuación se detalla el proceso y la organización:

### Estructura de Directorios
```
charts/
├── airflow/
│   ├── templates/
│   │   ├── configmap-dags.yaml
│   │   ├── deployment-scheduler.yaml
│   │   ├── deployment-webserver.yaml
│   │   ├── deployment-worker.yaml
│   │   ├── service.yaml
│   │   └── ...
│   ├── Chart.yaml
│   └── values.yaml
├── fastapi/
├── mlflow/
├── postgres/
└── ...
```

### Archivos Principales
1. **Chart.yaml**:
   - Archivo de configuración principal de cada chart
   - Define versión, nombre y descripción del chart
   - Especifica dependencias con otros charts
   - Establece tipo de chart (application/library)
   - Ejemplo:
     ```yaml
     apiVersion: v2
     name: airflow
     description: Apache Airflow para MLOps
     version: 1.0.0
     dependencies:
       - name: postgresql
         version: "12.1.6"
     ```

2. **values.yaml**:
   - Centraliza todas las variables configurables
   - Permite personalización sin modificar templates
   - Define valores por defecto para el despliegue
   - Facilita la reutilización y mantenimiento
   - Ejemplo:
     ```yaml
     image:
       repository: apache/airflow
       tag: 2.7.1
     resources:
       requests:
         memory: "1Gi"
         cpu: "500m"
     ```

3. **templates/**:
   - Contiene los manifiestos templatizados de Kubernetes
   - Usa la sintaxis Go template para variables dinámicas
   - Incluye helpers y funciones reutilizables
   - Permite lógica condicional y bucles

### Proceso de Migración
1. **Organización Inicial**:
   - Creación de estructura base de directorios por servicio
   - Definición de Chart.yaml y values.yaml iniciales

2. **Templatización de Manifiestos**:
   - Extracción de valores hardcodeados a variables
   - Implementación de helpers para nombres y labels
   - Uso de funciones de template para lógica condicional

3. **Gestión de Dependencias**:
   - Definición de dependencias entre charts
   - Configuración de orden de despliegue
   - Manejo de secretos y configuraciones compartidas

Esta estructura modular y la clara separación entre configuración y templates facilita el despliegue y mantenimiento de la infraestructura, proporcionando una base sólida para la guía de despliegue que se detalla en la siguiente sección.

## 2. Guía de Despliegue

### Primera Instalación

1. Asegurarse de tener un cluster de Kubernetes funcionando:
```bash
minikube stop
minikube start --cpus=6 --memory=10240 --disk-size=40g
```

2. Crear el namespace para MLOps:
```bash
kubectl create namespace mlops
```

3. Instalar los componentes por paquetes:

```bash
# Paquete 1: Componentes Base
# Instalar secrets y servicios base
helm install secrets ./secrets -n mlops
helm install postgres ./postgres -n mlops
helm install redis ./redis -n mlops
helm install minio ./minio -n mlops

# Verificar que los pods estén running antes de continuar
kubectl get pods -n mlops

# Paquete 2: Componentes MLOps Core
helm install mlflow ./mlflow -n mlops
helm install prometheus ./prometheus -n mlops
helm install grafana ./grafana -n mlops

# Verificar que los pods estén running antes de continuar
kubectl get pods -n mlops

# Paquete 3: Componentes de Orquestación y UI
helm install airflow ./airflow -n mlops
helm install fastapi ./fastapi -n mlops
helm install streamlit ./streamlit -n mlops

kubectl get pods -n mlops

```

### Actualización de Servicios Existentes

Si los servicios ya están desplegados y se necesita actualizarlos:

1. Para actualizar un componente específico:
```bash
helm upgrade [nombre-release] [nombre-chart] -n mlops
```

2. Si se necesita reinstalar completamente un paquete:
```bash
# Ejemplo para Paquete 3
# Desinstalar servicios del paquete
helm uninstall airflow fastapi streamlit -n mlops

# Eliminar recursos persistentes si es necesario
kubectl delete pvc -l "app in (airflow,fastapi,streamlit)" -n mlops

# Reinstalar servicios del paquete
helm install airflow ./airflow -n mlops
helm install fastapi ./fastapi -n mlops
helm install streamlit ./streamlit -n mlops
```

3. Para verificar el estado de los servicios:
```bash
# Verificar pods
kubectl get pods -n mlops

# Verificar servicios
kubectl get services -n mlops

# Verificar releases de Helm
helm list -n mlops
```

4. Port-Forwarding (nos quedamos en el puerto de airflow para encender los dags, y verificar que todos corran al menos una vez para acceder a los demás puertos mediante el port forward).

```bash
kubectl port-forward svc/airflow-webserver 8080:8080 -n mlops
kubectl port-forward svc/mlflow 5000:5000 -n mlops
kubectl port-forward svc/minio 9001:9001 -n mlops
kubectl port-forward svc/fastapi 8989:8989 -n mlops
kubectl port-forward svc/streamlit 8501:8501 -n mlops
kubectl port-forward svc/grafana 3000:3000 -n mlops

```


Cadena de comandos para pruebas iterativas, se recomienda eliminar o resetear minikube para continuar con el flujo sin residuos de ejecuciones anteriores 

```bash 
helm uninstall airflow fastapi streamlit mlflow prometheus grafana minio redis postgres secrets -n mlops
kubectl get all -n mlops
kubectl delete pvc --all -n mlops
kubectl delete namespace mlops
kubectl create namespace mlops
# Paquete 1: Componentes Base
helm install secrets ./secrets -n mlops
helm install postgres ./postgres -n mlops
helm install redis ./redis -n mlops
helm install minio ./minio -n mlops

# Verificar que los pods estén running antes de continuar
kubectl get pods -n mlops

# Paquete 2: Componentes MLOps Core
helm install mlflow ./mlflow -n mlops
helm install prometheus ./prometheus -n mlops
helm install grafana ./grafana -n mlops

# Verificar que los pods estén running antes de continuar
kubectl get pods -n mlops

# Paquete 3: Componentes de Orquestación y UI
helm install airflow ./airflow -n mlops
helm install fastapi ./fastapi -n mlops
helm install streamlit ./streamlit -n mlops

helm list -n mlops
kubectl get pods -n mlops

```

### Notas Importantes
- Asegurarse de que los recursos del cluster sean suficientes antes de la instalación
- Respetar el orden de instalación por paquetes para garantizar las dependencias
- Verificar que los servicios de cada paquete estén funcionando antes de instalar el siguiente
- Monitorear los logs de los pods en caso de errores durante el despliegue
- Considerar la persistencia de datos al realizar actualizaciones o reinstalaciones
- Para acceder a las interfaces web, usar port-forward o configurar ingress según sea necesario 


