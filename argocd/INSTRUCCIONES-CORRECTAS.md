# Instrucciones correctas para Argo CD

## Situación actual
Actualmente ya tienes Argo CD instalado en el namespace `argocd` usando `kubectl apply`. Los pods están en ejecución:

```
NAME                                                READY   STATUS    RESTARTS   AGE
argocd-application-controller-0                     1/1     Running   0          3m42s
argocd-applicationset-controller-6fbf568667-spcbp   1/1     Running   0          3m42s
argocd-dex-server-54b9c57895-z92x8                  1/1     Running   0          3m42s
argocd-notifications-controller-78d744c854-q6qtl    1/1     Running   0          3m42s
argocd-redis-6d89c85856-cbflf                       1/1     Running   0          3m42s
argocd-repo-server-5b85b6c97-zqjjw                  1/1     Running   0          3m42s
argocd-server-64f67b8649-ts8qx                      1/1     Running   0          3m42s
```

## Error al intentar instalar con Helm
El error que estás viendo:
```
helm install argocd argo/argo-cd -n argocd
Error: INSTALLATION FAILED: Unable to continue with install: ServiceAccount "argocd-application-controller" in namespace "argocd" exists and cannot be imported into the current release...
```

Esto ocurre porque estás intentando instalar con Helm en un namespace donde ya existe una instalación hecha con `kubectl apply`.

## Solución: Continuar con la instalación existente

Ya que Argo CD ya está instalado y funcionando, simplemente continúa con la configuración:

```bash
# Configurar el repositorio
kubectl apply -f argocd-repo-config.yaml

# Aplicar la definición de la aplicación
kubectl apply -f app.yaml
```

## Acceso a la interfaz de Argo CD

1. Exponer el servicio:
```bash
kubectl port-forward svc/argocd-server -n argocd 9090:443
```

2. Obtener la contraseña inicial:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```

3. Acceder a la interfaz en: https://localhost:9090
   - Usuario: admin
   - Contraseña: (obtenida en el paso anterior)

## Verificar la aplicación

Una vez en la interfaz de Argo CD, deberías ver tu aplicación "mlops-platform". Si no aparece:

```bash
kubectl apply -f app.yaml -n argocd
```

## Nota importante
No mezcles instalaciones con `kubectl` y Helm. Si ya has instalado con `kubectl`, continúa usando ese método. Si quieres usar Helm, primero debes eliminar completamente la instalación existente.