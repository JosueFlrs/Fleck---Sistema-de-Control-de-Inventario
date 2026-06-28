# =========================================================================
# CAPA DE CONSULTAS Y REQUERIMIENTOS DE DATOS - INVENTARIO ITU
# Reúne todas las funciones lógicas de acceso y manipulación de datos.
# Las rutas (vistas web) llaman a estas funciones para obtener información.
# =========================================================================

from datetime import date
from conexiones import get_sql_connection, get_mongo_collection

def _hardware_por_equipo():
    """Helper interno: Mapea todo el hardware de Mongo indexado por el 'equipo_id'."""
    coleccion = get_mongo_collection()
    if coleccion is None:
        return {}
    try:
        return {doc['equipo_id']: doc for doc in coleccion.find({}, {'_id': 0})}
    except Exception as e:
        print(f"[ERROR MONGO] No se pudo mapear hardware: {e}")
        return {}


def _proximo_equipo_id(conn):
    """Helper interno: Analiza los IDs en SQL para calcular el siguiente número de PC (Ej: PC-0005)."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT MAX(CAST(SUBSTRING(equipo_id, 4, 10) AS INT)) "
            "FROM equipo WHERE equipo_id LIKE 'PC-%'"
        )
        row = cursor.fetchone()
        siguiente = (row[0] or 0) + 1
    except Exception as e:
        print(f"[ERROR SQL] No se pudo calcular proximo id: {e}")
        siguiente = 1
    return f"PC-{siguiente:04d}"


def obtener_tecnicos():
    """Trae la lista de técnicos activos desde SQL Server para los dropdowns de los formularios."""
    conn = get_sql_connection()
    if conn is None:
        return []
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(
            "SELECT id, (nombre + ' ' + apellido) AS nombre "
            "FROM responsable "
            "WHERE tipo = 'tecnico' AND activo = 1 "
            "ORDER BY apellido, nombre"
        )
        return cursor.fetchall()
    except Exception as e:
        print(f"[ERROR SQL] No se pudieron traer tecnicos: {e}")
        return []
    finally:
        conn.close()


def obtener_equipos(aula_filtro='', responsable_filtro=''):
    """Trae todos los equipos de SQL filtrados opcionalmente por aula o responsable y les acopla su tipo desde Mongo."""
    conn = get_sql_connection()
    if conn is None:
        return []
    equipos = []
    try:
        cursor = conn.cursor(as_dict=True)
        query = """
            SELECT
                e.equipo_id                         AS id,
                e.numero_serie                      AS numero_serie,
                e.numero_banco                      AS numero_banco,
                e.estado                            AS estado,
                e.fecha_alta                        AS fecha_alta,
                e.fecha_proximo_mantenimiento       AS proximo_mantenimiento,
                u.edificio                          AS edificio,
                u.aula                              AS aula,
                (r.nombre + ' ' + r.apellido)       AS responsable
            FROM equipo e
            INNER JOIN ubicacion u   ON e.ubicacion_id   = u.id
            INNER JOIN responsable r ON e.responsable_id = r.id
            WHERE 1 = 1
        """
        params = []
        if aula_filtro:
            query += " AND u.aula LIKE %s"
            params.append(f"%{aula_filtro}%")
        if responsable_filtro:
            query += " AND (r.nombre + ' ' + r.apellido) LIKE %s"
            params.append(f"%{responsable_filtro}%")
        query += " ORDER BY e.equipo_id"
        cursor.execute(query, tuple(params))
        equipos = cursor.fetchall()
    except Exception as e:
        print(f"[ERROR SQL] Consulta de equipos fallo: {e}")
    finally:
        conn.close()

    # Cruce de datos: Traemos los tipos de hardware de Mongo para asignarlos a cada PC de SQL
    hw_map = _hardware_por_equipo()
    for eq in equipos:
        hw = hw_map.get(eq['id'])
        eq['tipo'] = hw.get('tipo', 'desktop') if hw else 'desktop'
    return equipos


def obtener_equipo(equipo_id):
    """Trae los detalles generales de una sola PC desde SQL Server."""
    conn = get_sql_connection()
    if conn is None:
        return None
    equipo = None
    try:
        cursor = conn.cursor(as_dict=True)
        query = """
            SELECT
                e.equipo_id                   AS id,
                e.numero_serie                AS numero_serie,
                e.numero_banco                AS numero_banco,
                e.estado                      AS estado,
                e.fecha_alta                  AS fecha_alta,
                e.fecha_proximo_mantenimiento AS proximo_mantenimiento,
                u.edificio                    AS edificio,
                u.aula                        AS aula,
                (r.nombre + ' ' + r.apellido) AS responsable
            FROM equipo e
            INNER JOIN ubicacion u   ON e.ubicacion_id   = u.id
            INNER JOIN responsable r ON e.responsable_id = r.id
            WHERE e.equipo_id = %s
        """
        cursor.execute(query, (equipo_id,))
        equipo = cursor.fetchone()
    except Exception as e:
        print(f"[ERROR SQL] Consulta de equipo {equipo_id} fallo: {e}")
    finally:
        conn.close()
    if equipo is not None:
        equipo.setdefault('piso', '—')
    return equipo


def obtener_hardware(equipo_id):
    """Trae las especificaciones detalladas de hardware de una PC desde MongoDB."""
    coleccion = get_mongo_collection()
    if coleccion is None:
        return None
    try:
        return coleccion.find_one({'equipo_id': equipo_id}, {'_id': 0})
    except Exception as e:
        print(f"[ERROR MONGO] Consulta de hardware {equipo_id} fallo: {e}")
        return None