#!/bin/bash
# Script simplificado para instalar Argo CD en un clúster de Kubernetes

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Crear namespace para Argo CD
echo -e "${CYAN}Creando namespace argocd...${NC}"
kubectl create namespace argocd

# Instalar Argo CD
echo -e "${CYAN}Instalando Argo CD...${NC}"
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