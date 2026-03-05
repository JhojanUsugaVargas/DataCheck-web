from werkzeug.security import check_password_hash
from cryptography.fernet import Fernet
import pyodbc

FERNET_KEY = b"Km4ESWSgjOjQhYDDmyPuIIfxXE62E9XWu6cOH0tyP70="
ENCRYPTED_CONN_STR = b"gAAAAABoxEgUMmBXS9TgOGz2_DM0StzjmWLK5LMaaLgkapsWByPhLWOpXaPl9o_zrkbUSQNM1nbev8dNDYQ9H4yRjSJ7d5UxgDq7xKWIH1PhyAv6q20LDEbm0YeORtMu47zFYcMwawT7w6OCZYAJdAxdcSBwBQwWdbZFC_xjF3NgFwdNJ-EcLIISqMRg3vlSyaMqfwh8Jy7oAqbp_ZgLcE9TQa2Alf4F8bgzhaduaTKqmzfYqtprBxw="

fernet = Fernet(FERNET_KEY)
CONN_STR = fernet.decrypt(ENCRYPTED_CONN_STR).decode()

# Posibles contraseñas a probar basadas en el patrón detectado
patterns = [
    "admin",
    "superadmin",
    "monitoreo",
    "Monitoreo",
    "admin123",
    "superadmin123",
    "Monitoreo123",
    "datacheck",
    "DataCheck"
]



try:
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("SELECT Username, PasswordHash FROM Users")
    users = cursor.fetchall()
    
    for user in users:
        username = user.Username
        stored_hash = user.PasswordHash
        print(f"Checking user: {username}")
        for p in patterns:
            if check_password_hash(stored_hash, p):
                print(f"  MATCH FOUND! User: {username}, Password: {p}")
                break
        else:
            print(f"  No match for {username} in current pattern list.")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
