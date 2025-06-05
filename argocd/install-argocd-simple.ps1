# Script simplificado para instalar Argo CD en un clúster de Kubernetes
# Este script debe ejecutarse en PowerShell con permisos adecuados

# Crear namespace para Argo CD
Write-Host "Creando namespace argocd..." -ForegroundColor Cyan
kubectl create namespace argocd

# Instalar Argo CD
Write-Host "Instalando Argo CD..." -ForegroundColor Cyan
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que los pods estén listos
Write-Host "Esperando a que los pods de Argo CD estén listos..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Aplicar la configuración del repositorio
Write-Host "Configurando el repositorio..." -ForegroundColor Cyan
kubectl apply -f argocd-repo-config.yaml

# Aplicar la definición de la aplicación
Write-Host "Aplicando la definición de la aplicación MLOps..." -ForegroundColor Cyan
kubectl apply -f app.yaml

# Obtener la contraseña inicial
Write-Host "Obteniendo la contraseña inicial de Argo CD..." -ForegroundColor Cyan
$password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
Write-Host "Usuario: admin" -ForegroundColor Green
Write-Host "Contraseña: $password" -ForegroundColor Green

# Configurar port-forward para acceder a la interfaz
Write-Host "Para acceder a la interfaz de Argo CD, ejecuta:" -ForegroundColor Yellow
Write-Host "kubectl port-forward svc/argocd-server -n argocd 8080:443" -ForegroundColor White
Write-Host "Luego accede a la interfaz en: https://localhost:8080" -ForegroundColor Green