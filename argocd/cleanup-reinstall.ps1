# Script para limpiar una instalación existente de Argo CD y reinstalarla
# Este script debe ejecutarse en PowerShell con permisos adecuados

# Eliminar la instalación existente de Argo CD
Write-Host "Eliminando la instalación existente de Argo CD..." -ForegroundColor Cyan
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que se eliminen los recursos
Write-Host "Esperando a que se eliminen los recursos..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Verificar si quedan recursos en el namespace
$resources = kubectl get all -n argocd
if ($resources) {
    Write-Host "Aún hay recursos en el namespace argocd. Eliminando el namespace completo..." -ForegroundColor Yellow
    kubectl delete namespace argocd
    Start-Sleep -Seconds 5
    kubectl create namespace argocd
} else {
    Write-Host "Todos los recursos han sido eliminados correctamente" -ForegroundColor Green
}

# Reinstalar Argo CD
Write-Host "Reinstalando Argo CD..." -ForegroundColor Cyan
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