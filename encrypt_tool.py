import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Cargar el archivo .env desde la carpeta backend
env_path = os.path.join('backend', '.env')
if not os.path.exists(env_path):
    # Intentar en el directorio actual si no existe backend/.env
    env_path = '.env'

load_dotenv(env_path)

def encrypt_string():
    fernet_key = os.environ.get('FERNET_KEY')
    if not fernet_key:
        print("❌ Error: No se encontró FERNET_KEY en el archivo .env")
        return

    print("--- Encriptador de Cadenas de Conexión ---")
    print(f"Usando llave: {fernet_key[:10]}...")
    
    raw_str = input("\nIngresa la nueva cadena de conexión (sin comillas): ").strip()
    
    if not raw_str:
        print("❌ Error: No ingresaste ninguna cadena.")
        return

    try:
        f = Fernet(fernet_key.encode())
        encrypted = f.encrypt(raw_str.encode()).decode()
        
        print("\n✅ Cadena encriptada generada con éxito:")
        print("-" * 50)
        print(encrypted)
        print("-" * 50)
        print("\nInstrucciones:")
        print(f"1. Abre tu archivo {env_path}")
        print("2. Reemplaza el valor de ENCRYPTED_CONN_STR con la cadena de arriba.")
        print("3. Guarda el archivo y reinicia la aplicación.")
        
    except Exception as e:
        print(f"❌ Error al encriptar: {e}")

if __name__ == "__main__":
    encrypt_string()
