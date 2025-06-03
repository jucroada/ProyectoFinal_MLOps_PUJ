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

```bash
docker compose exec mlops-postgres psql -U airflow -d airflow -c "\l"
docker compose exec mlops-postgres psql -U airflow -d airflow -c "\dt *.*"


```




**Nota:** Trabajaremos con fernet key

```plaintext
http://localhost:8080      #   airflow
http://localhost:9001      #   minio
http://localhost:5000      #   mlflow
http://localhost:8888        # jupyterlab
```

anotación, para hacer tunel usando port forwarding a traves de la conexión ssh de la vm 

Creación DAGS

```bash 
docker compose exec mlops-postgres psql -U airflow -d airflow -c "DROP SCHEMA raw_data CASCADE; DROP SCHEMA clean_data CASCADE;"
docker compose restart fastapi

```

ejemplos de prueba para la api

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

migración a kubernetes 

```bash
kubectl version --client 
```

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

El proceso de despliegue de kubernetes se hace por aparte, el readme para desplegarlo se encuentra en k8s




```bash
kubectl create namespace airflow-test
#kubectl config set-context --current --namespace=airflow-test
helm repo add apache-airflow https://airflow.apache.org
helm repo update
helm repo listThe output should include the apache-airflow repository:
helm install airflow apache-airflow/airflow -f values.yaml --namespace airflow-test --wait


helm uninstall airflow --namespace airflow-test
kubectl delete namespace airflow-test --wait=true
kubectl get namespaces

```

instalación directa al path de helm

```bash
helm repo update
helm install airflow apache-airflow/airflow -f values.yaml
helm uninstall airflow
kubectl get pods
kubectl describe pod <nombre-del-pod>
kubectl logs <nombre-del-pod>

kubectl delete pvc --all
kubectl delete secret --all


kubectl delete pod airflow-redis-0 --grace-period=0 --force
kubectl delete pod airflow-run-airflow-migrations-9b92k --grace-period=0 --force

```

reset pods
```bash
helm uninstall airflow
kubectl delete pvc --all
kubectl delete pv --all
kubectl delete secret --all
kubectl delete configmap --all

kubectl get pods
# Si ves alguno en Terminating:
kubectl delete pod <pod> --grace-period=0 --force

```


