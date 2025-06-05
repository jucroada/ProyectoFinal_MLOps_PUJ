# Solución al error de instalación de Argo CD

## Error encontrado
```
helm install argocd argo/argo-cd -n argocd -f argocd-values.yaml
Error: INSTALLATION FAILED: open argocd-values.yaml: The system cannot find the file specified.
```

## Causa
El error ocurre porque el comando `helm install` no puede encontrar el archivo `argocd-values.yaml`. Esto puede deberse a:
1. No estar en el directorio donde se encuentra el archivo
2. El archivo no existe o tiene un nombre diferente
3. Problemas de permisos para acceder al archivo

## Soluciones

### Opción 1: Instalar Argo CD sin usar el archivo de valores personalizado
```bash
# Crear el namespace para Argo CD
kubectl create namespace argocd

# Instalar Argo CD usando los manifiestos oficiales (recomendado)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

### Opción 2: Usar la ruta completa al archivo de valores
```bash
helm install argocd argo/argo-cd -n argocd -f c:/Users/julio/OneDrive/Documentos/Segundo\ Semestre/Operación\ Aprendizaje\ de\ Máquina/Talleres/ProyectoFinal_MLOps_PUJ/argocd/argocd-values.yaml
```

### Opción 3: Usar los scripts simplificados
Hemos creado scripts simplificados que no dependen del archivo de valores:

#### En Windows:
```powershell
.\install-argocd-simple.ps1
```

#### En Linux/macOS:
```bash
chmod +x install-argocd-simple.sh
./install-argocd-simple.sh
```

## Pasos después de la instalación

Una vez instalado Argo CD, continúa con:

1. Configurar el repositorio:
```bash
kubectl apply -f argocd-repo-config.yaml
```

2. Aplicar la definición de la aplicación:
```bash
kubectl apply -f app.yaml
```

3. Acceder a la interfaz:
```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

4. Obtener la contraseña inicial:
```bash
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d
```