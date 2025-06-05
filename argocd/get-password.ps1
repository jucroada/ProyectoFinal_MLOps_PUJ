# Script para obtener la contraseña inicial de Argo CD en Windows
$encodedPassword = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
$password = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encodedPassword))
Write-Host "Usuario: admin"
Write-Host "Contraseña: $password"