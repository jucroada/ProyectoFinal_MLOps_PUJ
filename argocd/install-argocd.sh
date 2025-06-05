#!/bin/bash
# Script para instalar Argo CD en un clúster de Kubernetes
# Este script debe ejecutarse en un entorno Linux/macOS

# Colores para mensajes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Verificar si kubectl está instalado
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl no está instalado o no está en el PATH${NC}"
    echo -e "${YELLOW}Por favor, instala kubectl antes de continuar: https://kubernetes.io/docs/tasks/tools/install-kubectl/${NC}"
    exit 1
else
    echo -e "${GREEN}kubectl está instalado correctamente${NC}"
fi

# Verificar conexión al clúster
if ! kubectl get nodes &> /dev/null; then
    echo -e "${RED}Error: No se puede conectar al clúster de Kubernetes${NC}"
    echo -e "${YELLOW}Asegúrate de que tu archivo kubeconfig esté configurado correctamente${NC}"
    exit 1
else
    echo -e "${GREEN}Conexión al clúster establecida correctamente${NC}"
fi

# Crear namespace para Argo CD
echo -e "${CYAN}Creando namespace argocd...${NC}"
kubectl create namespace argocd || echo -e "${YELLOW}El namespace argocd ya existe o hubo un error al crearlo${NC}"

# Instalar Argo CD
echo -e "${CYAN}Instalando Argo CD...${NC}"
if ! kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml; then
    echo -e "${RED}Error al instalar Argo CD${NC}"
    exit 1
fi

# Esperar a que los pods estén listos
echo -e "${CYAN}Esperando a que los pods de Argo CD estén listos...${NC}"
sleep 10
if ! kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=argocd-server -n argocd --timeout=300s; then
    echo -e "${YELLOW}Tiempo de espera agotado para los pods de Argo CD${NC}"
    echo -e "${YELLOW}Verifica el estado manualmente con: kubectl get pods -n argocd${NC}"
fi

# Aplicar la configuración de la aplicación
echo -e "${CYAN}Aplicando la definición de la aplicación MLOps...${NC}"
if ! kubectl apply -f app.yaml; then
    echo -e "${RED}Error al aplicar la definición de la aplicación${NC}"
else
    echo -e "${GREEN}Aplicación MLOps definida correctamente en Argo CD${NC}"
fi

# Obtener la contraseña inicial
echo -e "${CYAN}Obteniendo la contraseña inicial de Argo CD...${NC}"
PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)
echo -e "${GREEN}Usuario: admin${NC}"
echo -e "${GREEN}Contraseña: $PASSWORD${NC}"

# Configurar port-forward para acceder a la interfaz
echo -e "${CYAN}Configurando port-forward para acceder a la interfaz de Argo CD...${NC}"
echo -e "${YELLOW}Ejecuta el siguiente comando en una nueva terminal:${NC}"
echo -e "kubectl port-forward svc/argocd-server -n argocd 8080:443"
echo -e "${GREEN}Luego accede a la interfaz en: https://localhost:8080${NC}"

echo -e "${GREEN}Instalación de Argo CD completada${NC}"