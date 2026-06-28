#!/bin/bash

# =========================================================================
# desplegar.sh — Script de automatización de infraestructura para Ubuntu
# Proyecto: Inventario ITU
# =========================================================================

# Definición de colores para la terminal
VERDE='\033[0;32m'
AZUL='\033[0;34m'
AMARILLO='\033[1;33m'
ROJO='\033[0;31m'
SIN_COLOR='\033[0m'

echo -e "${AZUL}🚀 Iniciando despliegue de la infraestructura en Minikube...${SIN_COLOR}"

# 1. Crear el Namespace (La base de aislamiento)
echo -e "${AMARILLO}➔ Creando Namespace...${SIN_COLOR}"
kubectl apply -f namespace.yaml

# 2. Cargar configuraciones, scripts de inicio y secretos
echo -e "${AMARILLO}➔ Aplicando ConfigMaps y Secrets...${SIN_COLOR}"
kubectl apply -f mongo-init-configmap.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets/sqlserver-secret.yaml

# 3. Aplicar las Políticas de Red (Firewall interno)
echo -e "${AMARILLO}➔ Aplicando Network Policies...${SIN_COLOR}"
kubectl apply -f network-policies/

# 4. Configurar los servicios puente hacia las VMs externas (SQL y LDAP)
echo -e "${AMARILLO}➔ Configurando conexiones externas (SQL Server y LDAP)...${SIN_COLOR}"
kubectl apply -f services/ubicacion-db.yaml
kubectl apply -f services/ldap-service.yaml

# 5. Levantar la base de datos NoSQL MongoDB
echo -e "${AMARILLO}➔ Desplegando MongoDB (Almacenamiento + Pod + Servicio)...${SIN_COLOR}"
kubectl apply -f mongo-pvc.yaml
kubectl apply -f deployments/mongo-deployment.yaml
kubectl apply -f services/mongo-service.yaml

# 6. Levantar la aplicación web Flask (Frontend)
echo -e "${AMARILLO}➔ Desplegando Aplicación Web (Flask)...${SIN_COLOR}"
kubectl apply -f deployments/frontend-deployment.yaml
kubectl apply -f services/frontend-service.yaml

# 7. Control de espera y estado final
echo -e "${AZUL}⏳ Esperando 10 segundos a que los contenedores se estabilicen...${SIN_COLOR}"
sleep 10

echo -e "${VERDE}➔ Estado actual de los Pods en el namespace 'inventario':${SIN_COLOR}"
kubectl get pods -n inventario

echo -e "\n${VERDE}====================================================================${SIN_COLOR}"
echo -e "${VERDE}✅ ¡Despliegue finalizado con éxito!${SIN_COLOR}"
echo -e "Para abrir la app en tu navegador, ejecuta en otra terminal:"
echo -e "${AMARILLO}minikube service frontend-service -n inventario${SIN_COLOR}"
echo -e "${VERDE}====================================================================${SIN_COLOR}"