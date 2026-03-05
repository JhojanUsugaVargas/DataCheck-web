from waitress import serve
from app import app
import logging
import os

# Puerto por defecto o desde variable de entorno
port = int(os.environ.get('PORT', 5000))

if __name__ == '__main__':
    print(f"🚀 Iniciando servidor de PRODUCCIÓN en http://localhost:{port}")
    print("Servidor: Waitress (WSGI)")
    logging.info(f"Servidor Waitress iniciado en puerto {port}")
    
    # Servir la aplicación Flask con Waitress
    serve(app, host='0.0.0.0', port=port, threads=4)
