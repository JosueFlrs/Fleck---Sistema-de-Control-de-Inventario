# =========================================================
# Inventario ITU
#
# Archivo principal (Controlador) de la aplicación web Flask.
# Actúa como el "director de orquesta": recibe las peticiones 
# del navegador, interactúa con los modelos (conexiones/consultas)
# y devuelve las vistas (templates HTML) renderizadas.
# =========================================================

from datetime import date
from flask import (Flask, render_template, request, redirect, url_for, session, flash, jsonify)

# Importamos las piezas lógicas separadas en nuestros otros archivos
from config import SECRET_KEY
from conexiones import get_sql_connection, get_mongo_collection, ldap_autenticar
from consultas import (obtener_equipos, obtener_equipo, obtener_hardware, 
                       _hardware_por_equipo, _proximo_equipo_id, obtener_tecnicos)

# Inicializamos la aplicación Flask
app = Flask(__name__)
# Asignamos la clave secreta necesaria para manejar sesiones y mensajes flash de forma segura
app.secret_key = SECRET_KEY

# =========================================================
# RUTAS DE AUTENTICACIÓN
# =========================================================

@app.route('/')
def index():
    """
    Ruta raíz: Actúa como un semáforo. Si el usuario ya inició sesión,
    lo deja pasar al dashboard. Si no, lo manda a loguearse.
    """
    if session.get('username'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Gestiona el inicio de sesión. 
    Por GET: Muestra el formulario de login.
    Por POST: Recibe las credenciales y las valida contra el servidor LDAP.
    """
    if request.method == 'GET':
        return render_template('login.html')
        
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    if not username or not password:
        flash('Ingresa usuario y contrasena', 'danger')
        return redirect(url_for('login'))
        
    if ldap_autenticar(username, password):
        session['username'] = username  # Guardamos el usuario en la sesión cifrada
        flash(f'Bienvenido, {username}', 'success')
        return redirect(url_for('dashboard'))
        
    flash('Usuario o contrasena incorrectos', 'danger')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    """Limpia los datos de la sesión actual y devuelve al usuario a la pantalla de login."""
    session.clear()
    flash('Sesion cerrada correctamente', 'info')
    return redirect(url_for('login'))


# =========================================================
# RUTAS DEL PANEL E INVENTARIO
# =========================================================

@app.route('/dashboard')
def dashboard():
    """
    Pantalla principal tras iniciar sesión. 
    Calcula métricas rápidas (totales, mantenimientos) para mostrarlas en tarjetas.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
        
    equipos = obtener_equipos()
    stats = {
        'total_equipos': len(equipos),
        'total_aulas': len({e['aula'] for e in equipos}) if equipos else 0,
        'mantenimiento_pendiente': sum(1 for e in equipos if e.get('estado') == 'mantenimiento'),
        'total_hardware': len(_hardware_por_equipo()),
    }
    return render_template('dashboard.html', stats=stats)


@app.route('/inventario')
def inventario():
    """
    Lista todos los equipos registrados. 
    Lee los parámetros de la URL (?aula=...&responsable=...) para aplicar filtros de búsqueda.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
        
    aula_filtro        = request.args.get('aula', '').strip()
    responsable_filtro = request.args.get('responsable', '').strip()
    
    equipos = obtener_equipos(aula_filtro, responsable_filtro)
    return render_template('inventario.html',
                           equipos=equipos,
                           aula_filtro=aula_filtro,
                           responsable_filtro=responsable_filtro)


@app.route('/equipo/<equipo_id>')
def detalle_equipo(equipo_id):
    """
    Muestra la vista detallada de un equipo en particular.
    Une la información administrativa de SQL Server con las especificaciones técnicas de MongoDB.
    """
    if not session.get('username'):
        return redirect(url_for('login'))
        
    equipo = obtener_equipo(equipo_id)
    if not equipo:
        flash('Equipo no encontrado', 'warning')
        return redirect(url_for('inventario'))
        
    hardware = obtener_hardware(equipo_id)
    if hardware:
        equipo['tipo'] = hardware.get('tipo', 'desktop')
    else:
        equipo.setdefault('tipo', 'desktop')
        
    return render_template('detalle_equipo.html', equipo=equipo, hardware=hardware)


@app.route('/equipo/nuevo', methods=['GET', 'POST'])
def nuevo_equipo():
    """
    Maneja la creación de nuevos equipos.
    GET: Carga las listas desplegables de aulas y técnicos desde SQL para armar el formulario.
    POST: Procesa los datos, inserta el registro principal en SQL y luego las especificaciones en Mongo.
    """
    if not session.get('username'):
        return redirect(url_for('login'))

    if request.method == 'GET':
        conn = get_sql_connection()
        aulas = []
        if conn is not None:
            try:
                cursor = conn.cursor(as_dict=True)
                cursor.execute(
                    "SELECT id, (edificio + ' - ' + aula) AS nombre "
                    "FROM ubicacion ORDER BY edificio, aula")
                aulas = cursor.fetchall()
            except Exception as e:
                print(f"[ERROR SQL] No se pudieron traer aulas: {e}")
            finally:
                conn.close()
                
        # Pasamos la lista de tecnicos para armar las opciones del formulario (dropdown)
        tecnicos = obtener_tecnicos()
        return render_template('nuevo_equipo.html', aulas=aulas, tecnicos=tecnicos)

    # --- PROCESAMIENTO DEL POST ---
    numero_serie  = request.form.get('numero_serie', '').strip()
    tipo          = request.form.get('tipo', 'desktop').strip()
    aula_id       = request.form.get('aula_id', '').strip()
    numero_banco  = request.form.get('numero_banco', '').strip()
    responsable_id_form = request.form.get('responsable_id', '').strip()

    if not (numero_serie and aula_id and numero_banco):
        flash('Faltan datos obligatorios de ubicacion', 'danger')
        return redirect(url_for('nuevo_equipo'))

    conn = get_sql_connection()
    if conn is None:
        flash('No se pudo conectar a SQL Server. Equipo no registrado.', 'danger')
        return redirect(url_for('nuevo_equipo'))

    nuevo_id = None
    try:
        cursor = conn.cursor()

        # Determinar el ID del responsable desde el formulario o asignar un default
        if responsable_id_form:
            responsable_id = int(responsable_id_form)
        else:
            cursor.execute("SELECT TOP 1 id FROM responsable WHERE tipo = 'tecnico' AND activo = 1 ORDER BY id")
            fila = cursor.fetchone()
            responsable_id = fila[0] if fila else 1

        # Generamos el código autoincremental (Ej: PC-0012)
        nuevo_id = _proximo_equipo_id(conn)

        # INSERT en SQL Server (Datos administrativos)
        cursor.execute(
            """
            INSERT INTO equipo
                (equipo_id, numero_serie, numero_banco, ubicacion_id, responsable_id, estado, fecha_alta, fecha_proximo_mantenimiento)
            VALUES (%s, %s, %s, %s, %s, 'activo', %s, NULL)
            """,
            (nuevo_id, numero_serie, int(numero_banco), int(aula_id), responsable_id, date.today().isoformat()))
        conn.commit()
    except Exception as e:
        conn.rollback() # Cancelamos la transacción si hubo error
        print(f"[ERROR SQL] No se pudo insertar el equipo: {e}")
        flash(f'Error al registrar en SQL: {e}', 'danger')
        conn.close()
        return redirect(url_for('nuevo_equipo'))
    finally:
        if conn:
            conn.close()

    # INSERT del hardware en MongoDB (Specs técnicas)
    coleccion = get_mongo_collection()
    if coleccion is not None and nuevo_id:
        try:
            doc = {
                'equipo_id': nuevo_id,
                'tipo':       tipo,
                'fabricante': request.form.get('fabricante', '').strip(),
                'modelo':     request.form.get('modelo',     '').strip(),
                'cpu':        request.form.get('cpu',        '').strip(),
                'ram_gb':     int(request.form.get('ram_gb',   0) or 0),
                'disco_gb':   int(request.form.get('disco_gb', 0) or 0),
                'disco_tipo': request.form.get('disco_tipo', 'ssd').strip(),
                'so':         request.form.get('so',         '').strip(),
                'monitor':    request.form.get('monitor',    '').strip(),
                'mouse':      request.form.get('mouse')   == 'on',
                'teclado':    request.form.get('teclado') == 'on',
            }
            coleccion.insert_one(doc)
        except Exception as e:
            print(f"[ERROR MONGO] No se pudo insertar hardware: {e}")
            flash('Equipo creado en SQL, pero fallo el hardware en Mongo.', 'warning')
            return redirect(url_for('inventario'))

    flash(f'Equipo {nuevo_id} ({numero_serie}) registrado', 'success')
    return redirect(url_for('inventario'))


@app.route('/equipo/<equipo_id>/eliminar', methods=['POST'])
def eliminar_equipo(equipo_id):
    """
    Borra un equipo completo del sistema.
    Primero limpia sus relaciones en SQL (asignaciones, mantenimiento) para evitar errores de clave foránea,
    luego borra el registro principal y finalmente elimina el documento en Mongo.
    """
    if not session.get('username'):
        return redirect(url_for('login'))

    conn = get_sql_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM asignaciones_temporales WHERE equipo_id = %s", (equipo_id,))
            cursor.execute("DELETE FROM mantenimiento WHERE equipo_id = %s", (equipo_id,))
            cursor.execute("DELETE FROM equipo WHERE equipo_id = %s", (equipo_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"[ERROR SQL] No se pudo eliminar {equipo_id}: {e}")
            flash('No se pudo eliminar el equipo.', 'danger')
            conn.close()
            return redirect(url_for('inventario'))
        finally:
            conn.close()

    coleccion = get_mongo_collection()
    if coleccion is not None:
        try:
            coleccion.delete_one({'equipo_id': equipo_id})
        except Exception as e:
            print(f"[ERROR MONGO] No se pudo eliminar hardware {equipo_id}: {e}")

    flash(f'Equipo {equipo_id} eliminado', 'success')
    return redirect(url_for('inventario'))


# =========================================================
# APIS Y MONITOREO
# =========================================================

@app.route('/api/equipos')
def api_equipos():
    """Endpoint tipo API Rest: Devuelve la lista de equipos en formato JSON puro."""
    if not session.get('username'):
        return jsonify({'error': 'no autenticado'}), 401
    return jsonify(obtener_equipos())


@app.route('/health')
def health():
    """
    Ruta de control de salud (Healthcheck). 
    Sirve para que monitores externos verifiquen si la app tiene conexión a las bases de datos.
    """
    estado = {
        'sql':   get_sql_connection()    is not None,
        'mongo': get_mongo_collection()  is not None,
    }
    codigo = 200 if all(estado.values()) else 503
    return jsonify(estado), codigo


# =========================================================
# ARRANQUE DE LA APLICACIÓN
# =========================================================
if __name__ == '__main__':
    # Arranca el servidor de desarrollo en todas las interfaces (0.0.0.0) por el puerto 5000
    app.run(debug=True, host='0.0.0.0', port=5000)