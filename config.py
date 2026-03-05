"""
Configuración centralizada para DataCheck Web.
Reutiliza la conexión encriptada del proyecto original.
"""
import os
import pyodbc
import logging
from cryptography.fernet import Fernet

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Flask Secret Key ===
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'datacheck-web-secret-key-2026')

# === Gemini AI ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', 'AIzaSyDupv6Ox5ZnjPSdtPRkWj2FbsrOCFIF4wQ')

# === Database Connection (Fernet encrypted, same as original project) ===
FERNET_KEY = os.environ.get('FERNET_KEY', "Km4ESWSgjOjQhYDDmyPuIIfxXE62E9XWu6cOH0tyP70=").encode()
ENCRYPTED_CONN_STR = os.environ.get('ENCRYPTED_CONN_STR', "gAAAAABoxEgUMmBXS9TgOGz2_DM0StzjmWLK5LMaaLgkapsWByPhLWOpXaPl9o_zrkbUSQNM1nbev8dNDYQ9H4yRjSJ7d5UxgDq7xKWIH1PhyAv6q20LDEbm0YeORtMu47zFYcMwawT7w6OCZYAJdAxdcSBwBQwWdbZFC_xjF3NgFwdNJ-EcLIISqMRg3vlSyaMqfwh8Jy7oAqbp_ZgLcE9TQa2Alf4F8bgzhaduaTKqmzfYqtprBxw=").encode()


fernet = Fernet(FERNET_KEY)
CONN_STR = fernet.decrypt(ENCRYPTED_CONN_STR).decode()

# === AI DB Connection (for bot_sql_ai functionality) ===
AI_CONN_STR = (
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost;'
    'DATABASE=AsistenteSQL_AI;'
    'Trusted_Connection=yes;'
)


def get_db_connection(use_ai_db=False, dynamic_conn_str=None):
    """Establece conexión con la base de datos. Puede recibir una cadena dinámica."""
    try:
        if dynamic_conn_str:
            # Decrypt if it's bytes (stored encrypted in DB)
            if isinstance(dynamic_conn_str, bytes):
                try:
                    conn_str = fernet.decrypt(dynamic_conn_str).decode()
                except:
                    conn_str = dynamic_conn_str.decode() if isinstance(dynamic_conn_str, bytes) else dynamic_conn_str
            else:
                conn_str = dynamic_conn_str
        else:
            conn_str = AI_CONN_STR if use_ai_db else CONN_STR
            
        return pyodbc.connect(conn_str, autocommit=True)
    except pyodbc.Error as error:
        logging.error(f"Error al conectar a la base de datos: {str(error)}")
        return None

def get_available_contracts():
    """Recupera la lista de contratos activos."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Name FROM Contracts WHERE IsActive = 1")
        return [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    except:
        return []
    finally:
        conn.close()

def get_instances_by_contract(contract_id):
    """Recupera la lista de instancias para un contrato específico."""
    conn = get_db_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Name, ConnectionString FROM Instances WHERE ContractID = ? AND IsActive = 1", (contract_id,))
        return [{'id': row[0], 'name': row[1], 'conn_str': row[2]} for row in cursor.fetchall()]
    except:
        return []
    finally:
        conn.close()
