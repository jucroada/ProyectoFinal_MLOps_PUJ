#!/bin/bash
# Script para limpiar una instalación existente de Argo CD y reinstalarla

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Eliminar la instalación existente de Argo CD
echo -e "${CYAN}Eliminando la instalación existente de Argo CD...${NC}"
kubectl delete -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que se eliminen los recursos
echo -e "${CYAN}Esperando a que se eliminen los recursos...${NC}"
sleep 10

# Verificar si quedan recursos en el namespace
if kubectl get all -n argocd 2>/dev/null | grep -q .; then
    echo -e "${YELLOW}Aún hay recursos en el namespace argocd. Eliminando el namespace completo...${NC}"
    kubectl delete namespace argocd
    sleep 5
    kubectl create namespace argocd
else
    echo -e "${GREEN}Todos los recursos han sido eliminados correctamente${NC}"
fi

# Reinstalar Argo CD
echo -e "${CYAN}Reinstalando Argo CD...${NC}"
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Esperar a que los pods estén listos
echo -e "${CYAN}Esperando a que los pods de Argo CD estén listos...${NC}"
sleep 30

# Aplicar la configuración del repositorio
echo -e "${CYAN}Configurando el repositorio...${NC}"
kubectl apply -f argocd-repo-config.yaml

# Aplicar la definición de la aplicación
echo -e "${CYAN}Aplicando la definición de la aplicación MLOps...${NC}"
kubectl apply -f app.yaml

# Obtener la contraseña inicial
echo -e "${CYAN}Obteniendo la contraseña inicial de Argo CD...${NC}"
PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo -e "${GREEN}Usuario: admin${NC}"
echo -e "${GREEN}Contraseña: $PASSWORD${NC}"

# Configurar port-forward para acceder a la interfaz
echo -e "${YELLOW}Para acceder a la interfaz de Argo CD, ejecuta:${NC}"
echo "kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo -e "${GREEN}Luego accede a la interfaz en: https://localhost:8080${NC}"