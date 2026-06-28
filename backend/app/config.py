# =========================================================================
# CAPA DE CONFIGURACIÓN - INVENTARIO ITU
# Este archivo centraliza todas las variables de entorno y credenciales.
# Evita tener datos fijos (hardcodeados) dispersos por todo el código.
# =========================================================================

import os

# Clave secreta para firmar las cookies de las sesiones de Flask y usar flash()
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')

# Configuración para la conexión a la base de datos SQL (SQL Server)
SQL_HOST     = os.environ.get('SQL_HOST',     'ubicacion-db')
SQL_PORT     = int(os.environ.get('SQL_PORT', '1433'))
SQL_USER     = os.environ.get('SQL_USER',     'sa')
SQL_PASSWORD = os.environ.get('SQL_PASSWORD', '')
SQL_DATABASE = os.environ.get('SQL_DATABASE', 'Inventario')

# Configuración para la base de datos NoSQL (MongoDB - Hardware de equipos)
MONGO_HOST       = os.environ.get('MONGO_HOST',       'inventario-db')
MONGO_PORT       = int(os.environ.get('MONGO_PORT',   '27017'))
MONGO_DB         = os.environ.get('MONGO_DB',         'inventario')
MONGO_COLLECTION = os.environ.get('MONGO_COLLECTION', 'hardware')
MONGO_USER       = os.environ.get('MONGO_USER',       '')
MONGO_PASSWORD   = os.environ.get('MONGO_PASSWORD',   '')

# Configuración para el servicio de autenticación Active Directory / LDAP
LDAP_HOST   = os.environ.get('LDAP_HOST',   'ldap-service')
LDAP_PORT   = int(os.environ.get('LDAP_PORT', '389'))
LDAP_DOMAIN = os.environ.get('LDAP_DOMAIN', 'itu.local')