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

### Gestión de DAGs con GitHub

Para la gestión de los DAGs de Airflow se implementó una solución basada en **git-sync** que sincroniza automáticamente los DAGs desde GitHub:

**Puntos clave del proceso:**
- **Sincronización automática**: Los DAGs se obtienen directamente del repositorio GitHub sin necesidad de ConfigMaps locales
- **Git-sync configurado**: Se habilitó git-sync en todos los componentes de Airflow (scheduler, webserver, worker, triggerer)
- **Eliminación de ConfigMaps**: Se removieron las referencias a ConfigMaps de DAGs que eran innecesarias y causaban conflictos
- **Configuración centralizada**: En `values.yaml` se define el repositorio, rama y configuración de sincronización
- **Resolución de conflictos**: Se eliminaron volumeMounts obsoletos que impedían el correcto inicio de los componentes

**Configuración en values.yaml:**
```yaml
gitSync:
  enabled: true
  repository: "https://github.com/Serebas12/mlop_proyecto_final.git"
  branch: "main"
  subPath: "dags"
  image:
    repository: registry.k8s.io/git-sync/git-sync
    tag: v4.2.1
    pullPolicy: IfNotPresent
  resources:
    requests:
      memory: 64Mi
      cpu: 100m
    limits:
      memory: 128Mi
      cpu: 200m
```

Esta implementación garantiza que los DAGs estén siempre actualizados y elimina la necesidad de reconstruir imágenes o ConfigMaps cuando se modifiquen los workflows.

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
