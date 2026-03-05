from werkzeug.security import check_password_hash
from cryptography.fernet import Fernet
import pyodbc

FERNET_KEY = b"Km4ESWSgjOjQhYDDmyPuIIfxXE62E9XWu6cOH0tyP70="
ENCRYPTED_CONN_STR = b"gAAAAABoxEgUMmBXS9TgOGz2_DM0StzjmWLK5LMaaLgkapsWByPhLWOpXaPl9o_zrkbUSQNM1nbev8dNDYQ9H4yRjSJ7d5UxgDq7xKWIH1PhyAv6q20LDEbm0YeORtMu47zFYcMwawT7w6OCZYAJdAxdcSBwBQwWdbZFC_xjF3NgFwdNJ-EcLIISqMRg3vlSyaMqfwh8Jy7oAqbp_ZgLcE9TQa2Alf4F8bgzhaduaTKqmzfYqtprBxw="

fernet = Fernet(FERNET_KEY)
# Clean the connection string
CONN_STR = fernet.decrypt(ENCRYPTED_CONN_STR).decode()

# Posibles contraseñas a probar basadas en el patrón detectado
test_passwords = [
    "SuperCheck2026!",
    "AdminCheck2026!",
    "MonitorCheck2026!",
    "MonitoreoCheck2026!",
    "Admin2026!",
    "SuperAdmin2026!",
    "Monitor2026!",
    "DataCheck2026!"
]


def check():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT Username, PasswordHash, Role FROM Users")
        rows = cursor.fetchall()
        
        print(f"Checking {len(rows)} users against {len(test_passwords)} passwords...")
        
        for row in rows:
            found = False
            for pwd in test_passwords:
                if check_password_hash(row.PasswordHash, pwd):
                    print(f"MATCH: User={row.Username}, Role={row.Role}, Password={pwd}")
                    found = True
                    break
            if not found:
                print(f"NO MATCH for User={row.Username} (Role={row.Role})")
                
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    check()
