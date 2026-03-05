import base64
import os

# 1. Resolver requirements.txt
req_content = """flask>=3.0
pyodbc
psutil
cryptography
google-generativeai
duckduckgo-search
tabulate
waitress
pytest
pyotp
requests
python-dotenv
"""
with open('requirements.txt', 'w', encoding='utf-8') as f:
    f.write(req_content)
print("✅ requirements.txt actualizado.")

# 2. Obtener valores de .env
fernet = ""
gemini = ""
conn = ""

with open('backend/.env', 'r', encoding='utf-8') as f:
    for line in f:
        if line.startswith('FERNET_KEY='):
            fernet = line.split('=', 1)[1].strip()
        elif line.startswith('GEMINI_API_KEY='):
            gemini = line.split('=', 1)[1].strip()
        elif line.startswith('ENCRYPTED_CONN_STR='):
            conn = line.split('=', 1)[1].strip()

# 3. Base64 encode
b64_fernet = base64.b64encode(fernet.encode()).decode()
b64_gemini = base64.b64encode(gemini.encode()).decode()
b64_conn = base64.b64encode(conn.encode()).decode()

# 4. Resolver k8s/secrets.yaml
secrets_content = f"""apiVersion: v1
kind: Secret
type: Opaque
metadata:
  name: datacheck-secrets
  namespace: datacheck-web
data:
  FERNET_KEY: {b64_fernet}
  GEMINI_API_KEY: {b64_gemini}
  ENCRYPTED_CONN_STR: {b64_conn}
"""
with open('k8s/secrets.yaml', 'w', encoding='utf-8') as f:
    f.write(secrets_content)
print("✅ k8s/secrets.yaml actualizado.")
