"""
Configuración centralizada para DataCheck Web.
Reutiliza la conexión encriptada del proyecto original.
"""
import os
import pyodbc
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# === Cargar variables de entorno ===
load_dotenv()

# === Logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Flask Secret Key ===
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY')

# === Gemini AI ===
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# === Database Connection (Fernet encrypted, same as original project) ===
FERNET_KEY = os.environ.get('FERNET_KEY', "").encode()
ENCRYPTED_CONN_STR = os.environ.get('ENCRYPTED_CONN_STR', "").encode()
ENCRYPTED_AI_CONN_STR = os.environ.get('ENCRYPTED_AI_CONN_STR', "").encode()

# === reCAPTCHA ===
RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')
RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')


fernet = Fernet(FERNET_KEY)
CONN_STR = fernet.decrypt(ENCRYPTED_CONN_STR).decode()

# === AI DB Connection (for bot_sql_ai functionality) ===
if ENCRYPTED_AI_CONN_STR:
    try:
        AI_CONN_STR = fernet.decrypt(ENCRYPTED_AI_CONN_STR).decode()
    except:
        AI_CONN_STR = None
else:
    AI_CONN_STR = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=localhost;'
        'DATABASE=AsistenteSQL_AI;'
        'Trusted_Connection=yes;'
    )


def get_db_connection(use_ai_db=False, dynamic_conn_str=None):
    """Establece conexión con la base de datos. Puede recibir una cadena dinámica (bytes, hex or plain)."""
    try:
        if dynamic_conn_str:
            # Handle if it was stored as hex in session
            if isinstance(dynamic_conn_str, str) and len(dynamic_conn_str) > 100 and all(c in '0123456789abcdefABCDEF' for c in dynamic_conn_str[:50]):
                try:
                    dynamic_conn_str = bytes.fromhex(dynamic_conn_str)
                except:
                    pass

            # Decrypt if it's bytes (stored encrypted in DB)
            if isinstance(dynamic_conn_str, bytes):
                try:
                    conn_str = fernet.decrypt(dynamic_conn_str).decode()
                except:
                    # Maybe it's not encrypted or decryption failed
                    conn_str = dynamic_conn_str.decode(errors='ignore')
            else:
                conn_str = dynamic_conn_str
        else:
            conn_str = AI_CONN_STR if use_ai_db else CONN_STR
            
        if not conn_str:
            logging.error("No hay cadena de conexión disponible.")
            return None

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
