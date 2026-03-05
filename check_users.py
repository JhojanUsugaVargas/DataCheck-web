from cryptography.fernet import Fernet
import pyodbc

FERNET_KEY = b"Km4ESWSgjOjQhYDDmyPuIIfxXE62E9XWu6cOH0tyP70="
ENCRYPTED_CONN_STR = b"gAAAAABoxEgUMmBXS9TgOGz2_DM0StzjmWLK5LMaaLgkapsWByPhLWOpXaPl9o_zrkbUSQNM1nbev8dNDYQ9H4yRjSJ7d5UxgDq7xKWIH1PhyAv6q20LDEbm0YeORtMu47zFYcMwawT7w6OCZYAJdAxdcSBwBQwWdbZFC_xjF3NgFwdNJ-EcLIISqMRg3vlSyaMqfwh8Jy7oAqbp_ZgLcE9TQa2Alf4F8bgzhaduaTKqmzfYqtprBxw="

fernet = Fernet(FERNET_KEY)
CONN_STR = fernet.decrypt(ENCRYPTED_CONN_STR).decode()

print(f"Connecting to: {CONN_STR}")

try:
    conn = pyodbc.connect(CONN_STR)
    cursor = conn.cursor()
    cursor.execute("SELECT Username, Role, FullName FROM Users")
    with open("users_list.txt", "w") as f:
        for row in cursor.fetchall():
            f.write(f"USER:{row.Username}|ROLE:{row.Role}|NAME:{row.FullName}\n")
    print("DONE: Results written to users_list.txt")
    conn.close()
except Exception as e:
    with open("users_list.txt", "w") as f:
        f.write(f"ERROR:{e}\n")
    print(f"ERROR: {e}")



