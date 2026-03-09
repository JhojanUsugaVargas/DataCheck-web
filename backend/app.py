"""
DataCheck Web — Main Flask Application (Modularized)
Entry point that register Blueprints and global configurations.
"""
import os
import logging
from flask import Flask, render_template, session, redirect, url_for, jsonify, request
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.config import SECRET_KEY, get_db_connection, get_available_contracts, get_instances_by_contract, APP_VERSION

# Import Blueprints
from blueprints.auth_bp import auth_bp
from blueprints.admin_bp import admin_bp
from blueprints.dba_bp import dba_bp
from blueprints.chat_bp import chat_bp
from blueprints.feedback_bp import feedback_bp
from utils.decorators import login_required, role_required

app = Flask(__name__, 
            static_folder='../frontend/static', 
            template_folder='../frontend/templates')

# Inform Flask to trust reverse proxy headers, especially for prefix mapping
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

app.secret_key = SECRET_KEY
app.permanent_session_lifetime = 1800  # 30 minutes

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(dba_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(feedback_bp)

# Logging configuration
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@app.before_request
def log_request_info():
    logging.debug(f"[{request.remote_addr}] Request: {request.method} {request.url}")
    logging.debug(f"Headers: {dict(request.headers)}")

# ============================================================
#  INYECCIÓN DE VARIABLES GLOBALES EN TEMPLATES
# ============================================================
@app.context_processor
def inject_global_vars():
    # Extraer la variable de entorno, si no existe o termina en slash, la limpia
    base_url = os.environ.get('APP_BASE_URL', '').rstrip('/')
    recaptcha_enabled = os.environ.get('RECAPTCHA_ENABLED', 'true').lower()
    return dict(APP_BASE_URL=base_url, RECAPTCHA_ENABLED=recaptcha_enabled, APP_VERSION=APP_VERSION)

# ============================================================
#  MAIN ROUTES (General)
# ============================================================

@app.route('/')
@login_required
def index():
    contracts = get_available_contracts()
    current_contract_id = session.get('current_contract_id')
    current_instance_id = session.get('current_instance_id')
    
    # default contract if not set
    if not current_contract_id and contracts:
        current_contract_id = contracts[0]['id']
        session['current_contract_id'] = current_contract_id
    
    available_instances = []
    if current_contract_id:
        available_instances = get_instances_by_contract(current_contract_id)
        # default instance if not set
        if not current_instance_id and available_instances:
            session['current_instance_id'] = available_instances[0]['id']
            session['current_conn_str'] = available_instances[0].get('conn_str', '')
            current_instance_id = available_instances[0]['id']

    return render_template('index.html', 
                           username=session.get('username', 'Usuario'), 
                           full_name=session.get('full_name', 'Usuario'), 
                           role=session.get('role', 'Monitor'),
                           contracts=contracts,
                           instances=available_instances,
                           current_contract_id=current_contract_id,
                           current_instance_id=current_instance_id)

@app.route('/api/instances')
@login_required
def api_get_instances():
    contract_id = request.args.get('contract_id')
    if not contract_id: return jsonify([])
    
    instances = get_instances_by_contract(contract_id)
    # Solo devolver ID y Name al frontend por seguridad y para evitar errores de serialización (bytes)
    safe_instances = [{'id': inst['id'], 'name': inst['name']} for inst in instances]
    return jsonify(safe_instances)

@app.route('/api/instances/select', methods=['POST'])
@login_required
def api_select_instance():
    data = request.get_json()
    instance_id = data.get('instance_id')

    if not instance_id:
        return jsonify({'success': False, 'message': 'Falta el ID de la instancia'})

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error al conectar a la DB principal'})

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ConnectionString, ContractID FROM Instances WHERE ID = ?", (instance_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Instancia no encontrada'})

        conn_str = row[0]
        if isinstance(conn_str, bytes):
            conn_str = conn_str.hex()

        session['current_instance_id'] = instance_id
        session['current_conn_str'] = conn_str
        session['current_contract_id'] = row[1]
        
        return jsonify({'success': True, 'message': 'Instancia conectada'})
    finally:
        conn.close()

@app.route('/api/contracts/add', methods=['POST'])
@login_required
@role_required('Administrador')
def api_add_contract():
    data = request.get_json()
    name = data.get('name')
    if not name: return jsonify({'success': False})
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Contracts (Name, IsActive) VALUES (?, 1)", (name,))
        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()

@app.route('/api/instances/add', methods=['POST'])
@login_required
@role_required('Administrador')
def api_add_instance():
    data = request.get_json()
    contract_id = data.get('contract_id')
    name = data.get('name')
    conn_str = data.get('conn_str')
    
    if not all([contract_id, name, conn_str]):
        return jsonify({'success': False})

    from utils.config import fernet
    encrypted_conn = fernet.encrypt(conn_str.encode())

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Instances (ContractID, Name, ConnectionString, IsActive) VALUES (?, ?, ?, 1)",
                       (contract_id, name, encrypted_conn))
        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return jsonify({'error': 'No encontrado'}), 404

@app.errorhandler(500)
def server_error(e):
    logging.exception(f"Error interno del servidor: {e}")
    return jsonify({'error': 'Error interno del servidor'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
