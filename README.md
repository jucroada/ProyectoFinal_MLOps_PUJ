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
Rutas encontradas
/metrics con método GET usando Prometheus 
/health con método GET para verificar con status OK
/data con método GET con información necesaría `group_number` y `day`
/restart_data_generation con método GET con información necesaria `group_number` y `day`

Con lo que nuestras consultas a la api serán llevadas a cabo de 
```plaintext
http://10.43.101.108:80/data?group_number=6&day=Wednesday
http://10.43.101.108:80/restart_data_generation?group_number=6&day=Wednesday
```

