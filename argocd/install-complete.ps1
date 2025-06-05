# Script completo para instalar y configurar Argo CD en un clúster de Kubernetes limpio
# Este script debe ejecutarse en PowerShell con permisos adecuados

# Verificar si kubectl está instalado
try {
    kubectl version --client
    Write-Host "kubectl está instalado correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error: kubectl no está instalado o no está en el PATH" -ForegroundColor Red
    exit 1
}

# Verificar conexión al clúster
try {
    kubectl get nodes
    Write-Host "Conexión al clúster establecida correctamente" -ForegroundColor Green
} catch {
    Write-Host "Error: No se puede conectar al clúster de Kubernetes" -ForegroundColor Red
    Write-Host "¿Quieres iniciar Minikube? (S/N)" -ForegroundColor Yellow
    $respuesta = Read-Host
    if ($respuesta -eq "S" -or $respuesta -eq "s") {
        Write-Host "Iniciando Minikube con recursos suficientes..." -ForegroundColor Cyan
        minikube start --cpus=4 --memory=8192 --disk-size=40g
    } else {
        exit 1
    }
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
Start-Sleep -Seconds 30
kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tiempo de espera agotado para los pods de Argo CD" -ForegroundColor Yellow
    Write-Host "Verificando el estado de los pods..." -ForegroundColor Cyan
    kubectl get pods -n argocd
}

# Crear namespace para la aplicación
Write-Host "Creando namespace mlops..." -ForegroundColor Cyan
kubectl create namespace mlops
if ($LASTEXITCODE -ne 0) {
    Write-Host "El namespace mlops ya existe o hubo un error al crearlo" -ForegroundColor Yellow
}

# Aplicar la configuración del repositorio
Write-Host "Configurando el repositorio..." -ForegroundColor Cyan
kubectl apply -f argocd-repo-config.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al configurar el repositorio" -ForegroundColor Red
} else {
    Write-Host "Repositorio configurado correctamente" -ForegroundColor Green
}

# Aplicar la definición de la aplicación
Write-Host "Aplicando la definición de la aplicación MLOps..." -ForegroundColor Cyan
kubectl apply -f app.yaml
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al aplicar la definición de la aplicación" -ForegroundColor Red
} else {
    Write-Host "Aplicación MLOps definida correctamente en Argo CD" -ForegroundColor Green
}

# Obtener la contraseña inicial
Write-Host "Obteniendo la contraseña inicial de Argo CD..." -ForegroundColor Cyan
$encodedPassword = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$password = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedPassword))
Write-Host "Usuario: admin" -ForegroundColor Green
Write-Host "Contraseña: $password" -ForegroundColor Green

# Configurar port-forward para acceder a la interfaz
Write-Host "Para acceder a la interfaz de Argo CD, ejecuta:" -ForegroundColor Yellow
Write-Host "kubectl port-forward svc/argocd-server -n argocd 9090:443" -ForegroundColor White
Write-Host "Luego accede a la interfaz en: https://localhost:9090" -ForegroundColor Green

# Preguntar si desea iniciar port-forward ahora
Write-Host "¿Quieres iniciar port-forward ahora? (S/N)" -ForegroundColor Yellow
$respuesta = Read-Host
if ($respuesta -eq "S" -or $respuesta -eq "s") {
    Write-Host "Iniciando port-forward..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-Command", "kubectl port-forward svc/argocd-server -n argocd 9090:443"
    Write-Host "Port-forward iniciado. Accede a https://localhost:9090" -ForegroundColor Green
}

Write-Host "Instalación y configuración de Argo CD completada" -ForegroundColor Green