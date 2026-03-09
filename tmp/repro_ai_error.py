import sys
import os
from flask import Flask, session, request
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from blueprints.chat_bp import chat_bp
    from utils.config import SECRET_KEY
    
    app = Flask(__name__)
    app.secret_key = SECRET_KEY or 'test_key'
    app.register_blueprint(chat_bp)
    
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['logged_in'] = True
            sess['username'] = 'test_user'
            sess['user_id'] = 1
            sess['role'] = 'DBA'
        
        print("Probando pregunta AI de texto...")
        resp = client.post('/api/chat', 
                          data=json.dumps({'message': '¿Cómo hago un JOIN?'}),
                          content_type='application/json')
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.data.decode()}")
        
except Exception as e:
    print(f"Error en reproducción: {e}")
    import traceback
    traceback.print_exc()
