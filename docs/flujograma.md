graph TD
    %% Definición de colores basados en la imagen
    classDef base fill:#f9f9f9,stroke:#ccc,stroke-width:1px,color:#333,rx:20px,ry:20px
    classDef accion fill:#e8eaf6,stroke:#9fa8da,stroke-width:2px,color:#1a237e
    classDef decision fill:#fff3e0,stroke:#ffcc80,stroke-width:2px,color:#e65100
    classDef bd fill:#e8f5e9,stroke:#a5d6a7,stroke-width:2px,color:#1b5e20
    
    %% Nodos principales
    Inicio([Inicio]) :::base
    Acceso[Usuario accede a la app<br><small>nginx → pfSense → Flask :5000</small>] :::accion
    Sesion{¿Tiene sesión activa?} :::decision
    
    %% Rama de Login
    Login[Login] :::accion
    LDAP[Autenticar LDAP<br><small>AD :389</small>] :::bd
    Valido{¿Válido?} :::decision
    CrearSesion[Crear sesión] :::bd
    
    %% Dashboard y bifurcación
    Dash[Dashboard<br><small>Totales: equipos, aulas, hardware</small>] :::accion
    Accion{¿Qué acción realiza?} :::decision
    
    %% Rama 1: Ver lista
    Inv[Inventario] :::accion
    SqlSel[SQL Server<br><small>SELECT equipos</small>] :::bd
    Lista([Lista filtrable]) :::base
    
    %% Rama 2: Detalle
    DetalleApp[Detalle del equipo<br><small>equipo_id como clave</small>] :::accion
    SqlUbi[SQL Server<br><small>ubicación</small>] :::bd
    MongoHw[MongoDB<br><small>hardware</small>] :::bd
    Vista([Vista completa del equipo]) :::base
    
    %% Rama 3: Nuevo
    Form[Formulario] :::accion
    SqlMongoIns[SQL + Mongo<br><small>INSERT ambas BDs</small>] :::bd
    Flash([Flash + redirect]) :::base
    
    %% Nodo final
    Fin([Fin / Logout]) :::base

    %% Conexiones (Flujo)
    Inicio --> Acceso
    Acceso --> Sesion
    
    Sesion -- No --> Login
    Login --> LDAP
    LDAP --> Valido
    Valido -- No --> Login
    Valido -- Sí --> CrearSesion
    CrearSesion --> Dash
    
    Sesion -- Sí --> Dash
    Dash --> Accion
    
    %% Caminos de acción
    Accion -- Ver lista --> Inv
    Inv --> SqlSel
    SqlSel --> Lista
    Lista --> Fin
    
    Accion -- Detalle --> DetalleApp
    DetalleApp --> SqlUbi
    DetalleApp --> MongoHw
    SqlUbi --> Vista
    MongoHw --> Vista
    Vista --> Fin
    
    Accion -- Nuevo --> Form
    Form --> SqlMongoIns
    SqlMongoIns --> Flash
    Flash --> Fin