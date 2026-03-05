# Dockerfile para DataCheck Web
FROM python:3.11-slim

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/keyrings/microsoft.gpg \
    && echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/11/prod bullseye main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

<<<<<<< HEAD
# Copiar código
=======
# Copiar el resto de la aplicación (incluyendo backend y frontend)
>>>>>>> ad5aa99 (Cambios en Dockerfile, secrets y requirements)
COPY . .

# Puerto de la aplicación
EXPOSE 5000

<<<<<<< HEAD
# Ejecutar aplicación
CMD ["python", "run_prod.py"]
=======
# Comando para ejecutar la aplicación usando Waitress
# Se ejecuta desde la raíz indicando la ruta al script de producción
CMD ["python", "backend/run_prod.py"]
>>>>>>> ad5aa99 (Cambios en Dockerfile, secrets y requirements)
