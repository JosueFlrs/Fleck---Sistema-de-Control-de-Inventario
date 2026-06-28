# 🖥️ Plataforma de Inventario Seguro (EGI — ITU)

Un ecosistema centralizado e híbrido diseñado para el control de activos informáticos en laboratorios. Este proyecto combina autenticación corporativa distribuida (Active Directory/LDAP), segmentación estricta de bases de datos (SQL Server + MongoDB), un perímetro de red blindado por hardware virtual (pfSense) y una arquitectura de microservicios robusta orquestada nativamente sobre **Kubernetes (Minikube)**.

---

## 🏗️ Arquitectura de Cero Confianza (Zero-Trust)

El sistema opera bajo un esquema de **JOIN lógico en Backend**. La API desarrollada en Flask unifica las consultas: extrae los datos topológicos y de asignación desde la base relacional y los complementa dinámicamente usando el identificador común `equipo_id` para traer las especificaciones técnicas desde la base documental.

```text
[ Usuario / Cliente Web ]
           │
           ▼ (HTTP)
   [ Firewall pfSense ]  ◀─── (192.168.1.254 - Única Puerta de Enlace)
           │
           ▼ (NAT Port Forwarding -> :5000)
  [ Clúster de Minikube ] ─── (Host Ubuntu VM: 192.168.1.30)
           │
           ├──► [ Pod: Backend Flask ]
           │          │
           │          ├──► [ Pod: MongoDB ] ─── (Interno Clúster: :27017)
           │          │
           │          ├──► [ VM Windows: SQL Server ] ─── (Externo: 192.168.1.20:1433)
           │          │
           │          └──► [ VM Windows: Active Directory ] ─── (Externo: 192.168.1.10:389)
```

### Matriz de Direccionamiento de Red Aislada

> 💡 **Decisión de Diseño Crítica**: Se implementó una **Red Interna Pura en VirtualBox (`itu-lan`)**. Al remover adaptadores NAT independientes de las máquinas virtuales, se garantiza por topología física que ningún componente pueda saltearse el firewall perimetral pfSense. Es un entorno hermético y 100% portable para la instancia de defensa.

| Componente de Infraestructura | IP Estática | Puerta de Enlace | Servidor DNS | Sistema Operativo |
| :--- | :--- | :--- | :--- | :--- |
| **Perímetro**: pfSense Firewall | `192.168.1.254` | — | — | pfSense 2.8.1 |
| **Directorio**: Active Directory | `192.168.1.10` | `192.168.1.254` | `127.0.0.1` (Local) | Windows Server 2022 |
| **Relacional**: SQL Server Express | `192.168.1.20` | `192.168.1.254` | `192.168.1.10` | Windows Server 2022 |
| **Orquestador**: Minikube Clúster | `192.168.1.30` | `192.168.1.254` | `192.168.1.10` | Ubuntu Server |

---

## 🗂️ Anatomía del Repositorio Organizado

```text
inventario-egi/
├── backend/                   # Microservicio API Flask (Lógica del Sistema)
│   ├── app/                   # Código fuente (app.py, consultas.py, conexiones.py)
│   │   ├── static/            # Estilos CSS unificados (styles.css) e imágenes
│   │   └── templates/         # Vistas dinámicas Jinja2 en modo oscuro moderno
│   ├── Dockerfile             # Receta Slim optimizada con compiladores del sistema (gcc)
│   └── requirements.txt       # Congelación estricta de dependencias cruzadas
│
├── sql/                       # Persistencia Relacional (Instancia Windows Física)
│   ├── schema.sql             # Estructura DDL (Tablas de control, aulas y responsables)
│   └── data.sql               # Registros iniciales de consistencia
│
├── mongo/                     # Persistencia Documental Automatizada
│   └── init.js                # Script para inicializar Mongo
│
├── kubernetes/                # Declaración de Infraestructura Programada
│   ├── namespace.yaml         # Aislamiento lógico ('inventario')
│   ├── deployments/           # Ciclo de vida de Pods (Flask y MongoDB Engine)
│   ├── services/              # Abstracción de red interna y puentes de Endpoints externos
│   └── network-policies/      # Restricciones Calico de conectividad mínima indispensable
│
├── desplegar.sh               # Orquestador Bash interactivo para entornos Ubuntu
├── README.md
└── .gitignore
```

---

## 👥 Organización del Grupo de Trabajo y Ramas

Para garantizar la integridad del código, el desarrollo inicial sobre la rama `main` mutó hacia una asignación estructurada de responsabilidades por componentes:

* **Sofía Bazán** — Arquitectura perimetral, topología virtual e ingeniería de redes en pfSense.
* **Milagros Carrillo** — Control de identidades, federación LDAP e integración institucional AD.
* **Julián Méndez** — Ingeniería de datos relacionales, esquemas transaccionales en SQL Server.
* **Fernando Castro** — Administración NoSQL, empaquetado de microservicios en Kubernetes y modelado de políticas Zero-Trust con Calico. *(Nota técnica: Sus contribuciones iniciales en el motor NoSQL y políticas se unificaron directamente mediante merges supervisados en la línea de desarrollo principal).*

---

## 🚀 Despliegue Automatizado del Ecosistema

### Secuencia de Encendido de Máquinas Virtuales
1. `VM 1`: Active Directory / DNS Core (`192.168.1.10`)
2. `VM 2`: SQL Server Engine (`192.168.1.20`)
3. `VM 3`: pfSense Firewall / Gateway (`192.168.1.254`)
4. `VM 4`: Ubuntu Server / Minikube Clúster (`192.168.1.30`)

### Inicialización en la Terminal de Ubuntu

Una vez dentro de la máquina de Minikube, ejecuta los siguientes comandos para compilar el código local e iniciar el despliegue automático del firewall interno, bases de datos y frontend web:

```bash
# 1. Asegurar el inicio del entorno con el plugin de Calico activo
minikube start --cni=calico

# 2. Conectar la consola al entorno de ejecución interno del clúster
eval $(minikube docker-env)

# 3. Compilar la imagen de la aplicación Flask
docker build -t inventario-egi .

# 4. Otorgar permisos y ejecutar el script automatizado
chmod +x desplegar.sh
./desplegar.sh
```

Al finalizar el script, abre una segunda terminal para enlazar el servicio con tu navegador mediante el comando:
```bash
minikube service frontend-service -n inventario
```