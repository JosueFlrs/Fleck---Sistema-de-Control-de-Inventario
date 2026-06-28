# Configuración y Hardening de SQL Server con Integración Active Directory

**Proyecto Integrador EGI — Plataforma de Inventario Seguro**
Instituto Tecnológico Universitario (ITU) · Dominio: `itu.local`

---

## 1. Objetivo Arquitectónico

Establecer la base de datos relacional (SQL Server Express 2022) como el motor central de ubicación y control patrimonial. El sistema debe operar bajo un esquema de red hermético (Zero-Trust), siendo accesible exclusivamente por la API de backend (Minikube). La autenticación y autorización se encuentran 100% federadas mediante Active Directory (AD), aplicando estrictamente el Principio de Menor Privilegio (PoLP) a través de Roles de Seguridad Globales (RBAC).

---

## 2. Topología del Entorno

| Componente | Especificación Técnica |
| :--- | :--- |
| **Motor de Base de Datos** | SQL Server Express 2022 |
| **Instancia Nombrada** | `ITULAB` (Host: `ITUSRV002.itu.local`) |
| **Herramienta de Gestión** | SSMS — SQL Server Management Studio v20+ |
| **Infraestructura Host** | Windows Server 2022 (IP Fija: `192.168.1.20`) |
| **Esquema Relacional** | `Inventario` |
| **Federación de Identidades** | Active Directory (`itu.local` - DC: `192.168.1.10`) |

---

## 3. Configuración de Acceso a Red y Firewall Interno

Por razones de seguridad, las instancias Express aíslan su tráfico por defecto. Para permitir la comunicación exclusiva con el clúster de microservicios, se implementaron las siguientes reglas perimetrales:

### 3.1. Habilitación del Protocolo TCP/IP
1. Desde **SQL Server Configuration Manager** → *Configuración de red de SQL Server* → *Protocolos de `ITULAB`*.
2. Habilitación explícita del protocolo **TCP/IP**.
3. En propiedades de TCP/IP → Pestaña *Direcciones IP* → Sección *IPAll* → **Puerto TCP: `1433`**.
4. Reinicio forzado del servicio del motor.

### 3.2. Hardening Perimetral (Windows Defender Firewall)
Se bloqueó todo el tráfico de entrada, creando una única regla de excepción direccional. Se autoriza el tráfico hacia el puerto 1433 **únicamente** si el origen es el host físico donde opera Minikube (`192.168.1.30`):

```cmd
netsh advfirewall firewall add rule name="SQL-Server-1433-Minikube-Allow" dir=in action=allow protocol=TCP localport=1433 remoteip=192.168.1.30
```

### 3.3. Certificación de Enlace
Validación exitosa del socket TCP desde el entorno Linux (Ubuntu/Minikube):
```bash
nc -zv 192.168.1.20 1433
# Expected output: Connection to 192.168.1.20 1433 port [tcp/ms-sql-s] succeeded!
```

---

## 4. Estructura del Repositorio de Datos (`db-sql/`)

El modelo relacional (`Inventario`) se inicializa mediante scripts estandarizados versionados en el repositorio:
1. `schema.sql` — Define la estructura DDL (Data Definition Language).
2. `seed-data.sql` — Inyecta registros de prueba DML (Data Manipulation Language).

**Tablas Principales:** `ubicacion`, `responsable`, `equipo`, `asignaciones_temporales`, `mantenimiento`.
> 💡 **Llave de Integración:** La entidad `equipo` utiliza el atributo `equipo_id` (ej. `PC-0001`) como *Clave Foránea Lógica* para enlazar las especificaciones de hardware almacenadas en la base documental NoSQL (MongoDB).

---

## 5. Modelo RBAC (Role-Based Access Control) vía Active Directory

La administración de usuarios individuales no existe en el motor de SQL Server. Los permisos se delegan íntegramente a los Grupos de Seguridad Globales de Active Directory, garantizando un punto único de control de identidades institucionales.

### 5.1. Matriz de Roles y Privilegios

| Perfil Funcional | Grupo de Seguridad (AD) | Nivel de Privilegio SQL | Usuarios Asociados (Ejemplo) |
| :--- | :--- | :--- | :--- |
| **Administrador de Infra** | `Grupo_BD_Admin` | Control Total (`sysadmin`) | AdminAndres, AdminFernando |
| **Responsable Técnico** | `Grupo_BD_Inventario_C` | Lectura / Escritura Comercial | TecMarina, TecCarina |
| **Personal Docente** | `Grupo_BD_Inventario_R` | Solo Lectura de Datos | ProfZalazar, ProfOsmel |

### 5.2. Proceso de Enlace en SSMS (Mapeo de Logins)
Para conectar los grupos del dominio con los roles del motor:
1. *Seguridad* → *Inicios de sesión* → **Nuevo inicio de sesión...**
2. Modo: *Autenticación de Windows*.
3. Búsqueda → Tipos de Objeto: **Grupos** → Ubicación: Dominio **itu.local**.
4. Asignación de Roles según la matriz técnica:

| Grupo AD Mapeado | Nivel de Scope | Roles Asignados |
| :--- | :--- | :--- |
| `itu\Grupo_BD_Admin` | Servidor (Instancia) | `sysadmin` |
| `itu\Grupo_BD_Inventario_C` | Base de Datos (`Inventario`) | `db_datareader` + `db_datawriter` |
| `itu\Grupo_BD_Inventario_R` | Base de Datos (`Inventario`) | `db_datareader` |

> *Los grupos técnicos y docentes (`_C` y `_R`) tienen denegado por diseño cualquier rol a nivel Servidor.*

---

## 6. Auditoría y Validación de Permisos

Se ejecutaron pruebas de penetración lógica (suplantación de token Kerberos) para validar la restricción de comandos `INSERT/UPDATE/DELETE` en usuarios sin privilegios.

**Test Vector: Perfil Docente (Lectura Estricta)**
```cmd
runas /user:itu\ProfZalazar "ssms.exe"
```

**Ejecución de Query (Validación de Comportamiento):**
```sql
USE Inventario;

-- Intento 1: DQL (Data Query Language)
SELECT * FROM equipo; 
-- Resultado: OK (Datos retornados).

-- Intento 2: DML (Data Manipulation Language)
INSERT INTO ubicacion (edificio, aula, capacidad_equipos) VALUES ('Mendoza', 'Lab Redes', 15);
-- Resultado: ERROR. The INSERT permission was denied on the object 'ubicacion'.
```
*Las mismas sentencias ejecutadas bajo una sesión de perfil Técnico (`itu\TecMarina`) completan la transacción exitosamente, confirmando el cumplimiento del Principio de Menor Privilegio.*

---

## 7. Estado del Despliegue (Checklist Final)

- [x] Motor SQL Server Express 2022 aprovisionado.
- [x] Protocolo TCP/IP activo en puerto 1433.
- [x] Reglas del Firewall de Windows restringidas a IPs específicas.
- [x] Estructura DDL (`schema.sql`) y datos semilla (`seed-data.sql`) aplicados.
- [x] Organización de Grupos de Seguridad Global creados en Active Directory (`itu.local`).
- [x] Logins de Autenticación de Windows enlazados y mapeados a los grupos AD.
- [x] Pruebas de lectura/escritura certificadas según el rol del usuario.
- [x] Interfaz Flask configurada para autenticar el login de la aplicación contra LDAP.
- [x] Consolidación de la decisión de arquitectura relacional final.