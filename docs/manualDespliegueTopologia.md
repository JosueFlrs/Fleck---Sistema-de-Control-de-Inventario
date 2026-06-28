# Manual Técnico de Arquitectura e Interconexión Híbrida: Windows Server, SQL Server y Clúster Linux

> **Aviso Operativo sobre Topologías de Hardware**
>
> | Rol del Servidor | Entorno B (Recursos Óptimos) |
> | :--- | :--- | :--- |
> | **Active Directory (AD/LDAP)** | `192.168.1.10` |
> | **SQL Server Engine** | `192.168.1.20` (VM Dedicada) |
> | **Clúster Minikube (Backend/Web)** | `192.168.1.30` |
> 

---

## 1. Diseño Lógico del Ecosistema

* **Control de Identidades (Active Directory - `192.168.1.10`):** Actúa como el único proveedor de verdad para la autenticación institucional. El personal docente, técnico y administrativo posee credenciales centralizadas. Bajo el principio de mínimo privilegio, los perfiles de alumnos **no existen como cuentas de dominio**, ya que no requieren acceso operativo a la red corporativa.
* **Persistencia Relacional (SQL Server):** Administra el mapa topológico del equipamiento, asignaciones temporales y control patrimonial. Los alumnos son tratados exclusivamente como entidades de datos (cadenas de texto/legajos) dentro de los registros transaccionales de préstamos.
* **Orquestación de Contenedores (Linux Minikube - `192.168.1.30`):** Entorno de microservicios que aloja la API (Flask) y el motor documental documental (MongoDB). Establece puentes de red seguros hacia el exterior del clúster para consumir los servicios de SQL y LDAP.

---

## 2. Aprovisionamiento del Motor Relacional

1. Se desplegó **SQL Server Express 2022** como servicio nativo en Windows Server 2022 bajo la instancia nombrada **`ITULAB`**.
2. Se instaló la suite de administración **SQL Server Management Studio (SSMS)**.
3. Se garantizó el aislamiento inicial omitiendo la vinculación con servicios en la nube (Azure), operando estrictamente mediante Autenticación de Windows local.

---

## 3. Resolución de Anomalías del Proveedor WMI (Bug `[0x80041010]`)

*Nota de contingencia: Este paso se documenta como solución estándar frente a fallos de inicialización del Administrador de Configuración de SQL Server, comúnmente causados por latencias durante la instalación de dependencias en Windows Server 2022.*

Frente a la pérdida de comunicación con el proveedor WMI, se forzó la recompilación del archivo de objetos administrados (`.mof`):
1. Ejecución de terminal (`cmd`) con elevación de privilegios (Administrador).
2. Reconstrucción de la arquitectura nativa del manejador:
   ```cmd
   mofcomp "%programfiles(x86)%\Microsoft SQL Server\160\Shared\sqlmgmprovider.mof"
   ```
3. El compilador confirmó el procesamiento, restaurando inmediatamente el acceso al panel de configuración de red del motor.

---

## 4. Estabilización de Sockets y Protocolo TCP/IP

Las ediciones Express bloquean conexiones externas por defecto. Para permitir el enrutamiento desde el clúster de Kubernetes, se configuró un puerto estático:

1. Ingreso a `SQLServerManager16.msc`.
2. Navegación hacia: *Configuración de red de SQL Server* → *Protocolos de ITULAB*.
3. Habilitación del protocolo **TCP/IP**.
4. En las Propiedades de TCP/IP, sección **IPAll**:
   * **Puertos dinámicos TCP:** Se eliminó cualquier valor numérico, dejándolo en blanco para suprimir la aleatoriedad de puertos en cada reinicio.
   * **Puerto TCP:** Se fijó explícitamente el valor estándar **`1433`**.
5. Reinicio del servicio desde el panel general para impactar los registros.

**Certificación de escucha local (CMD):**
```cmd
netstat -an | find "1433"
```
*Output esperado: `TCP 0.0.0.0:1433 0.0.0.0:0 LISTENING`*

---

## 5. Habilitación de Autenticación Mixta para Microservicios

Para que el backend interactúe con el motor, la instancia debe aceptar credenciales SQL más allá del entorno Windows.

1. Modificación de las directivas del registro mediante CMD (Administrador):
   ```cmd
   sqlcmd -S localhost -E -Q "EXEC xp_instance_regwrite N'HKEY_LOCAL_MACHINE', N'Software\Microsoft\MSSQLServer\MSSQLServer', N'LoginMode', REG_DWORD, 2"
   ```
2. Activación y asignación de credenciales del superusuario para la cadena de conexión interna:
   ```cmd
   sqlcmd -S localhost -E -Q "ALTER LOGIN sa ENABLE"
   sqlcmd -S localhost -E -Q "ALTER LOGIN sa WITH PASSWORD = 'SuPasswordSeguro123!'"
   ```
3. **Reinicio obligatorio** del servicio `SQL Server (ITULAB)`.

---

## 6. Hardening Perimetral Zero-Trust (Firewall)

Se implementó una restricción de origen en el Firewall de Windows para evadir el escaneo de puertos de segmentos no autorizados.

**Regla de Permiso Direccional:**
```cmd
netsh advfirewall firewall add rule name="Ingreso SQL 1433 Minikube" dir=in action=allow protocol=TCP localport=1433 remoteip=192.168.1.30
```

**Justificación Arquitectónica:** El atributo `remoteip=192.168.1.30` restringe la visibilidad del puerto de bases de datos de forma exclusiva a la máquina virtual que aloja el clúster de Kubernetes. Todo paquete proveniente de una IP ajena se descarta silenciosamente.

---

## 7. Certificación de Conectividad Cruzada

Validación de la apertura de sockets desde el sistema Linux (Cliente) hacia el entorno Windows (Servidor):

```bash
# Ejecutar desde terminal Ubuntu (Host Minikube)
nc -zv 192.168.1.10 1433  # Para Entorno A
nc -zv 192.168.1.20 1433  # Para Entorno B
```
*Output de éxito: `Connection to 192.168.1.X 1433 port [tcp/ms-sql-s] succeeded!`*

---

## 8. Federación de Privilegios AD ↔ SQL Server

Se delegó el control de accesos al controlador de dominio mediante un mapeo directo de Grupos Globales a Roles del motor de base de datos.

**Mapeo de Identidades Implementado:**

| Unidad en Directorio Activo | Rol SQL Asignado | Capacidad Efectiva |
| :--- | :--- | :--- |
| `itu.local\Grupo_BD_Admin` | `sysadmin` (Motor Completo) | Administración estructural. |
| `itu.local\Grupo_BD_Inventario_C` | `db_datareader` + `db_datawriter` | Mutación de datos (Carga/Edición). |
| `itu.local\Grupo_BD_Inventario_R` | `db_datareader` (BD Inventario) | Consultas de solo lectura. |

---

## 9. Despliegue de Datos e Integración NoSQL

El modelo relacional fue adaptado exitosamente y opera en paralelo con la base de datos documental.
* **Modelo Estructural:** Scripts `schema.sql` y `seed-data.sql` ejecutados y consolidados.
* **Llave de Unión (Join Lógico):** El atributo primario `equipo_id` (ej. `PC-0001`) funciona como el identificador maestro compartido. Flask consulta la topología física en SQL y, con el mismo ID, extrae el perfil del hardware de la base de datos documental MongoDB que corre dentro del clúster.

---

## 10. Hitos Alcanzados y Cierre del Ecosistema

La infraestructura se encuentra completamente operativa, habiendo finalizado de forma exitosa las siguientes integraciones en la capa de Kubernetes:

* **Servicios Externos (`Endpoints`):** Los puentes `ubicacion-db` y `ldap-service` fueron configurados, enrutando el tráfico interno del clúster hacia los nodos físicos de Windows Server.
* **Inicialización Automatizada:** Se implementó un recurso `ConfigMap` que inyecta código semilla directamente al motor MongoDB en su primer arranque, eliminando la configuración manual.
* **Seguridad Calico (Network Policies):** El namespace opera bajo una política `default-deny-all`, abriendo exclusivamente los puertos 5000 (Frontend), 27017 (Mongo), 1433 (SQL) y 389 (LDAP).
* **Despliegue Continuo (Bash):** Automatización consolidada mediante el script `desplegar.sh` nativo para entornos Ubuntu.
* **Interfaz de Usuario:** Implementación de un diseño Frontend "Split-Screen" responsivo en modo oscuro utilizando componentes de Bootstrap 5.3.
