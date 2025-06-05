# Guía de Instalación de Argo CD para MLOps Platform

Esta guía detalla los pasos para implementar Argo CD y configurar el despliegue continuo de la plataforma MLOps.

## Requisitos previos

- Kubernetes cluster (Minikube, Docker Desktop, K3s, EKS, GKE, AKS, etc.)
- kubectl configurado para acceder al clúster
- Helm (opcional, para instalación alternativa)

## Instalación de Argo CD

### Opción 1: Instalación con scripts automatizados

#### En Windows:
1. Abre PowerShell como administrador
2. Navega al directorio donde se encuentra el script
3. Ejecuta:
   ```powershell
   .\install-argocd.ps1
   ```

#### En Linux/macOS:
1. Abre una terminal
2. Navega al directorio donde se encuentra el script
3. Haz el script ejecutable y ejecútalo:
   ```bash
   chmod +x install-argocd.sh
   ./install-argocd.sh
   ```

### Opción 2: Instalación manual

1. Crea el namespace para Argo CD:
   ```bash
   kubectl create namespace argocd
   ```

2. Instala Argo CD:
   ```bash
   kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
   ```

   Alternativamente, puedes usar Helm:
   ```bash
   helm repo add argo https://argoproj.github.io/argo-helm
   helm repo update
   helm install argocd argo/argo-cd -n argocd -f argocd-values.yaml
   ```

3. Espera a que todos los pods estén en estado "Running":
   ```bash
   kubectl get pods -n argocd
   ```

4. Aplica la definición de la aplicación:
   ```bash
   kubectl apply -f app.yaml
   ```

## Acceso a la interfaz de Argo CD

### Opción 1: Port-forward
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```
Accede a la interfaz en: https://localhost:8080

### Opción 2: Exponer como LoadBalancer (entornos cloud)
```bash
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "LoadBalancer"}}'
```

### Credenciales iniciales
- Usuario: admin
- Contraseña: Obtén la contraseña inicial con:
  ```bash
  kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
  ```

## Verificación de la instalación

1. Instala la CLI de Argo CD:
   - Windows (con Chocolatey): `choco install argocd-cli`
   - macOS (con Homebrew): `brew install argocd`
   - Linux: [Instrucciones oficiales](https://argo-cd.readthedocs.io/en/stable/cli_installation/)

2. Inicia sesión desde la CLI:
   ```bash
   argocd login localhost:8080
   ```

3. Verifica el estado de la aplicación:
   ```bash
   argocd app get mlops-platform
   argocd app sync mlops-platform
   ```

## Configuración de sincronización automática

La aplicación ya está configurada para sincronización automática en el archivo `app.yaml` con:

```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

Esto significa que:
- Argo CD sincronizará automáticamente cuando detecte cambios en el repositorio
- Eliminará recursos que ya no estén definidos en Git (prune)
- Revertirá cambios manuales en el clúster para mantener la consistencia con Git (selfHeal)

## Solución de problemas comunes

### La aplicación no se sincroniza
- Verifica que el repositorio sea accesible desde el clúster
- Comprueba los logs de Argo CD: `kubectl logs -n argocd deployment/argocd-repo-server`
- Fuerza una sincronización manual: `argocd app sync mlops-platform`

### Error de acceso al repositorio
- Si es un repositorio privado, configura las credenciales:
  ```bash
  kubectl create secret generic git-creds --from-literal=username=<username> --from-literal=password=<password> -n argocd
  kubectl label secret git-creds -n argocd argocd.argoproj.io/secret-type=repository
  ```

### Problemas con Helm
- Verifica que los charts de Helm sean válidos: `helm lint charts/`
- Comprueba los valores predeterminados: `helm template charts/`