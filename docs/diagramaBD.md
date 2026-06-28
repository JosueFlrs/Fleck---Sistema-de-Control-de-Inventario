erDiagram
    %% Relaciones (Conectores lógicos)
    ubicacion ||--o{ equipo : "aloja"
    responsable ||--o{ equipo : "supervisa"
    equipo ||--o{ mantenimiento : "recibe"
    responsable ||--o{ mantenimiento : "ejecuta"
    equipo ||--o{ asignacionesTemporales : "asignado en"
    responsable ||--o{ asignacionesTemporales : "toma prestado"

    %% Tablas y sus atributos en camelCase
    equipo {
        varchar equipoId PK
        varchar numeroSerie
        smallint numeroBanco
        int ubicacionId FK
        int responsableId FK
        enum estado
        date fechaAlta
        date fechaUltimoMantenimiento
        date fechaProximoMantenimiento
        text observaciones
    }

    ubicacion {
        int id PK
        varchar edificio
        varchar aula
        smallint capacidadEquipos
    }

    responsable {
        int id PK
        varchar nombre
        varchar apellido
        enum tipo
        varchar email
        varchar legajo
        varchar telefono
        tinyint activo
    }

    mantenimiento {
        int id PK
        varchar equipoId FK
        int tecnicoId FK
        enum tipo
        date fechaInicio
        date fechaFin
        text descripcion
        decimal costo
    }

    asignacionesTemporales {
        int id PK
        varchar equipoId FK
        int responsableId FK
        date fechaInicio
        date fechaFinEstimada
        date fechaDevolucion
        enum estado
    }