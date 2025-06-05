# Script para instalar Argo CD en un clúster de Kubernetes
# Este script debe ejecutarse en PowerShell con permisos adecuados

# Verificar si kubectl está instalado
try {
    kubectl version --client
    Write-Host "kubectl está instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error: kubectl no está instalado o no está en el PATH" -ForegroundColor Red
    Write-Host "Por favor, instala kubectl antes de continuar: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/" -ForegroundColor Yellow
    exit 1
}

# Verificar conexión al clúster
try {
    kubectl get nodes
    Write-Host "Conexión al clúster establecida correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error: No se puede conectar al clúster de Kubernetes" -ForegroundColor Red
    Write-Host "Asegúrate de que tu archivo kubeconfig esté configurado correctamente" -ForegroundColor Yellow
    exit 1
}

# Crear namespace para Argo CD
Write-Host "Creando namespace argocd..." -ForegroundColor Cyan
kubectl create namespace argocd
if ($LASTEXITCODE -ne 0) {
    Write-Host "El namespace argocd ya existe o hubo un error al crearlo" -ForegroundColor Yellow
}

# Instalar Argo CD
Write-Host "Instalando Argo CD..." -ForegroundColor Cyan
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al instalar Argo CD" -ForegroundColor Red
    exit 1
}

# Esperar a que los pods estén listos
Write-Host "Esperando a que los pods de Argo CD estén listos..." -ForegroundColor Cyan
Start-Sleep -Seconds 10
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tiempo de espera agotado para los pods de Argo CD" -ForegroundColor Yellow
    Write-Host "Verifica el estado manualmente con: kubectl get pods -n argocd" -ForegroundColor Yellow
}

# Aplicar la configuración de la aplicación
Write-Host "Aplicando la definición de la aplicación MLOps..." -ForegroundColor Cyan
kubectl apply -f app.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al aplicar la definición de la aplicación" -ForegroundColor Red
} else {
    Write-Host "Aplicación MLOps definida correctamente en Argo CD" -ForegroundColor Green
}

# Obtener la contraseña inicial
Write-Host "Obteniendo la contraseña inicial de Argo CD..." -ForegroundColor Cyan
$password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
Write-Host "Usuario: admin" -ForegroundColor Green
Write-Host "Contraseña: $password" -ForegroundColor Green

# Configurar port-forward para acceder a la interfaz
Write-Host "Configurando port-forward para acceder a la interfaz de Argo CD..." -ForegroundColor Cyan
Write-Host "Ejecuta el siguiente comando en una nueva ventana de PowerShell:" -ForegroundColor Yellow
Write-Host "kubectl port-forward svc/argocd-server -n argocd 8080:443" -ForegroundColor White
Write-Host "Luego accede a la interfaz en: https://localhost:8080" -ForegroundColor Green

Write-Host "Instalación de Argo CD completada" -ForegroundColor Green