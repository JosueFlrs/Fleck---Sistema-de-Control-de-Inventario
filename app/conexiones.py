# =========================================================================
# CAPA DE CONEXIONES - INVENTARIO ITU
# Contiene las funciones encargadas de establecer los enlaces a los
# motores de base de datos (SQL, Mongo) y al protocolo de autenticación (LDAP).
# =========================================================================

from datetime import date
import pymssql
from pymongo import MongoClient
from ldap3 import Server, Connection, ALL

from config import (SQL_HOST, SQL_PORT, SQL_USER, SQL_PASSWORD, SQL_DATABASE,
                    MONGO_HOST, MONGO_PORT, MONGO_DB, MONGO_COLLECTION, MONGO_USER, MONGO_PASSWORD,
                    LDAP_HOST, LDAP_PORT, LDAP_DOMAIN)

def get_sql_connection():
    """Establece y devuelve una conexión activa a SQL Server."""
    try:
        return pymssql.connect(
            server=SQL_HOST, port=SQL_PORT,
            user=SQL_USER, password=SQL_PASSWORD,
            database=SQL_DATABASE, timeout=5, login_timeout=5,
        )
    except Exception as e:
        print(f"[ERROR SQL] No se pudo conectar a SQL Server: {e}")
        return None

def get_mongo_collection():
    """Establece la conexión a MongoDB y devuelve la colección de hardware."""
    try:
        uri = (f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"
               if MONGO_USER else f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping') # Lanza un ping para validar que el servicio responde
        return client[MONGO_DB][MONGO_COLLECTION]
    except Exception as e:
        print(f"[ERROR MONGO] No se pudo conectar a MongoDB: {e}")
        return None

def ldap_autenticar(nombreUsuario, contrasenia):
    """Valida credenciales y devuelve el rol del usuario basado en sus grupos de AD."""
    try:
        usuarioPrincipal = (nombreUsuario if '@' in nombreUsuario else f"{nombreUsuario}@{LDAP_DOMAIN}")
        servidorLdap = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL, connect_timeout=5)
        conexionAd = Connection(servidorLdap, user=usuarioPrincipal, password=contrasenia, auto_bind=True)

        conexionAd.search(
            search_base='DC=itu,DC=local', 
            search_filter=f'(userPrincipalName={usuarioPrincipal})',
            attributes=['memberOf']
        )

        rolAsignado = 'lectura'
        
        if conexionAd.entries:
            gruposUsuario = conexionAd.entries[0].memberOf.values
            textoGrupos = str(gruposUsuario)
            
            # Si pertenece al grupo de técnicos o admin, le damos control total
            if 'Grupo_AD_Tecnicos' in textoGrupos or 'Grupo_AD_Admin' in textoGrupos:
                rolAsignado = 'tecnico'

        conexionAd.unbind()
        return True, rolAsignado
        
    except Exception as error:
        print(f"[INFO LDAP] Bind fallido para '{nombreUsuario}': {error}")
        return False, None