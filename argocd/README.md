# Implementación de Argo CD para MLOps Platform

Este directorio contiene los archivos necesarios para implementar Argo CD y configurar el despliegue continuo de la plataforma MLOps.

## Instalación rápida

Ejecuta el script de instalación completo:

```bash
# En Windows (PowerShell)
.\install-complete.ps1

# En Linux/macOS
chmod +x install-complete.sh
./install-complete.sh
```

## Instalación manual paso a paso

### 1. Iniciar Minikube con recursos suficientes

```bash
minikube start --cpus=4 --memory=10240 --disk-size=40g
```

### 2. Instalar Argo CD

```bash
# Crear namespace
kubectl create namespace argocd

# Instalar Argo CD
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que los pods estén listos
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s

# Observar pods
kubectl get pods -n argocd

```

### 3. Configurar el repositorio y la aplicación

```bash
# Aplicar configuración del repositorio
kubectl apply -f argocd/argocd-repo-config.yaml

# Aplicar definición de la aplicación
kubectl apply -f argocd/app.yaml
```

### 4. Acceder a Argo CD

```bash
# Obtener contraseña (Linux/macOS)
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d

# Obtener contraseña (Windows PowerShell)
$password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
Write-Host "Contraseña: $password"

# Exponer la interfaz web
kubectl port-forward svc/argocd-server -n argocd 9999:443
```

Accede a https://localhost:9999 con:
- Usuario: admin
- Contraseña: (obtenida en el paso anterior)

### 5. Sincronizar la aplicación

Desde la interfaz web, haz clic en "SYNC" en la aplicación mlops-platform.

O desde la línea de comandos:
```bash
argocd app sync mlops-platform
```

## Estructura de archivos

- `app.yaml`: Definición de la aplicación Argo CD que apunta a los charts de Helm
- `argocd-repo-config.yaml`: Configuración del repositorio Git
- `install-complete.ps1`/`install-complete.sh`: Scripts de instalación completa

## Repositorio monitoreado

Esta configuración está configurada para monitorear el repositorio:
**https://github.com/jucroada/ProyectoFinal_MLOps_PUJ.git**

## Solución de problemas

### Error al instalar con Helm después de kubectl
Si ya instalaste Argo CD con kubectl, no intentes instalar con Helm en el mismo namespace.

### Pods en estado Pending
Verifica los recursos disponibles en tu clúster:
```bash
kubectl describe pods -n argocd
```

### Error de conexión al repositorio
Verifica que el repositorio sea accesible y que las credenciales sean correctas:
```bash
kubectl logs -n argocd deployment/argocd-repo-server
```