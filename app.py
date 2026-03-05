"""
DataCheck Web — Main Flask Application
Replica la funcionalidad de main.py y bot_sql_ai.py en una interfaz web.
"""
import os
import re
import logging
import io
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from datetime import datetime

from config import get_db_connection, get_available_contracts, get_instances_by_contract, SECRET_KEY, GEMINI_API_KEY, fernet
from auth import login_required, role_required, authenticate, generate_mfa_secret, verify_mfa_token

# === Gemini AI Setup ===
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-2.5-flash')
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False
    logging.warning("Gemini AI no disponible. El asistente SQL AI estará limitado.")

# === DuckDuckGo Search ===
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = 1800  # 30 minutes

@app.before_request
def log_request_info():
    if not request.path.startswith('/static'):
        logging.info(f"Petición recibida: {request.method} {request.path}")

def get_active_conn():
    """Retorna una conexión a la instancia seleccionada en sesión, o a la DB principal si no hay selección."""
    dynamic_conn_encrypted = session.get('current_conn_str')
    if dynamic_conn_encrypted:
        try:
            # Intentar usar la conexión dinámica (config.get_db_connection maneja el desencriptado)
            return get_db_connection(dynamic_conn_str=dynamic_conn_encrypted)
        except Exception as e:
            logging.error(f"Error al usar conexión dinámica: {e}")
    
    # Si falla o no hay, usar la default
    return get_db_connection()


# ============================================================
#  PÁGINAS HTML
# ============================================================
@app.route('/login')
def login_page():
    if session.get('logged_in'):
        return redirect(url_for('index'))
    return render_template('login.html')


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

@app.route('/api/instances', methods=['GET'])
@login_required
def api_get_instances():
    contract_id = request.args.get('contract_id', type=int)
    if not contract_id:
        return jsonify([])
    
    instances = get_instances_by_contract(contract_id)
    # Solo devolver ID y Name al frontend por seguridad y para evitar errores de serialización (bytes)
    safe_instances = [{'id': inst['id'], 'name': inst['name']} for inst in instances]
    return jsonify(safe_instances)

@app.route('/api/instances/select', methods=['POST'])
@login_required
def api_select_instance():
    data = request.get_json()
    instance_id = data.get('instance_id')
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ConnectionString, ContractID FROM Instances WHERE ID = ?", (instance_id,))
        row = cursor.fetchone()
        if row:
            session['current_instance_id'] = instance_id
            session['current_conn_str'] = row[0]
            session['current_contract_id'] = row[1]
            return jsonify({'success': True})
    finally:
        conn.close()
    
    return jsonify({'success': False, 'message': 'Instancia no encontrada'}), 404


@app.route('/api/contracts/add', methods=['POST'])
@login_required
@role_required('administrador')
def api_add_contract():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'success': False, 'message': 'Nombre requerido'}), 400
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Contracts (Name) VALUES (?)", (name,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Contrato creado'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/instances/add', methods=['POST'])
@login_required
@role_required('administrador')
def api_add_instance():
    data = request.get_json()
    contract_id = data.get('contract_id')
    name = data.get('name')
    conn_str = data.get('conn_str')
    
    if not all([contract_id, name, conn_str]):
        return jsonify({'success': False, 'message': 'Todos los campos son requeridos'}), 400
    
    # Encriptar la cadena de conexión antes de guardarla
    encrypted_conn = fernet.encrypt(conn_str.encode())
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Instances (ContractID, Name, ConnectionString) VALUES (?, ?, ?)", 
                       (contract_id, name, encrypted_conn))
        conn.commit()
        return jsonify({'success': True, 'message': 'Instancia creada'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ============================================================
#  AUTH API
# ============================================================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    user_data = authenticate(username, password)
    
    if user_data:
        # Check if MFA is required
        if user_data.get('mfa_enabled'):
            # If token is provided in the request
            token = data.get('token')
            if not token:
                return jsonify({
                    'success': False, 
                    'requires_mfa': True, 
                    'message': 'Se requiere código de autenticación'
                })
            
            # Verify token
            if not verify_mfa_token(user_data.get('mfa_secret'), token):
                return jsonify({'success': False, 'message': 'Código MFA inválido'}), 401

        # Complete login
        session.permanent = True
        session['logged_in'] = True
        session['username'] = user_data['username']
        session['role'] = user_data['role'].strip()
        session['full_name'] = user_data['full_name']
        return jsonify({'success': True, 'message': f'¡Bienvenido, {user_data["full_name"]}!'})
    
    return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


# ============================================================
#  USER PROFILE & ADMIN API
# ============================================================
@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    new_password = data.get('password')
    full_name = data.get('full_name')
    username = session.get('username')

    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor()
        if new_password:
            # Check if user is Admin before allowing password change
            if session.get('role') != 'Admin':
                return jsonify({'error': 'Solo los administradores pueden cambiar contraseñas.'}), 403
                
            from werkzeug.security import generate_password_hash
            hashed = generate_password_hash(new_password)
            cursor.execute("UPDATE Users SET PasswordHash = ?, FullName = ? WHERE Username = ?", (hashed, full_name, username))
        else:
            cursor.execute("UPDATE Users SET FullName = ? WHERE Username = ?", (full_name, username))
        
        conn.commit()
        session['full_name'] = full_name
        return jsonify({'success': True, 'message': 'Perfil actualizado correctamente'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/mfa/setup', methods=['GET'])
@login_required
def mfa_setup():
    """Genera un nuevo secreto MFA y devuelve la URI para el QR."""
    username = session.get('username')
    secret = generate_mfa_secret()
    
    # Store temporary secret in session until verified
    session['temp_mfa_secret'] = secret
    
    # Create provisioning URI
    import pyotp
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name="DataCheck Web")
    
    # Generate QR Code base64
    import qrcode
    import base64
    from io import BytesIO
    
    img = qrcode.make(provisioning_uri)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({
        'success': True,
        'secret': secret,
        'qr_code': f"data:image/png;base64,{img_str}"
    })

@app.route('/api/mfa/activate', methods=['POST'])
@login_required
def mfa_activate():
    """Verifica el primer token y activa MFA permanentemente."""
    data = request.get_json()
    token = data.get('token')
    secret = session.get('temp_mfa_secret')
    username = session.get('username')
    
    if not secret or not token:
        return jsonify({'success': False, 'error': 'Datos faltantes'}), 400
        
    if verify_mfa_token(secret, token):
        # Save to DB
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE Users SET MFASecret = ?, MFAEnabled = 1 WHERE Username = ?", (secret, username))
            conn.commit()
            session.pop('temp_mfa_secret', None)
            return jsonify({'success': True, 'message': 'MFA activado con éxito'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()
    else:
        return jsonify({'success': False, 'error': 'Código inválido'}), 400

@app.route('/api/profile/photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No se encontró el archivo'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'Archivo sin nombre'}), 400
    
    # Simple check for image types
    if not file.content_type.startswith('image/'):
        return jsonify({'error': 'El archivo debe ser una imagen'}), 400

    username = session.get('username')
    photo_data = file.read()

    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Error de conexión'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET ProfilePhoto = ? WHERE Username = ?", (photo_data, username))
        conn.commit()
        return jsonify({'success': True, 'message': 'Foto de perfil actualizada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/profile/photo/<username>')
def get_profile_photo(username):
    conn = get_db_connection()
    if not conn: return "Error de conexión", 500

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT ProfilePhoto FROM Users WHERE Username = ?", (username,))
        row = cursor.fetchone()
        if row and row[0]:
            from flask import send_file
            import io
            return send_file(io.BytesIO(row[0]), mimetype='image/jpeg')
        return redirect(url_for('static', filename='default-avatar.png'))
    except Exception as e:
        return str(e), 500
    finally:
        conn.close()

@app.route('/api/admin/users', methods=['GET'])
@login_required
@role_required('administrador')
def get_users():
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Error de conexión'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Username, FullName, Role, CreatedAt FROM Users")
        users = []
        for row in cursor.fetchall():
            users.append({
                'username': row[0],
                'full_name': row[1],
                'role': row[2],
                'created_at': str(row[3])
            })
        return jsonify(users)
    finally:
        conn.close()

@app.route('/api/admin/users/add', methods=['POST'])
@login_required
@role_required('administrador')
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name')
    role = data.get('role', 'DBA')

    if not all([username, password, full_name]):
        return jsonify({'error': 'Faltan datos obligatorios'}), 400

    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash(password)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (Username, PasswordHash, FullName, Role) VALUES (?, ?, ?, ?)",
                       (username, hashed, full_name, role))
        conn.commit()
        return jsonify({'success': True, 'message': f'Usuario {username} creado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/users/reset_password', methods=['POST'])
@login_required
@role_required('administrador')
def reset_password():
    data = request.get_json()
    username = data.get('username')
    new_password = data.get('password')

    if not username or not new_password:
        return jsonify({'error': 'Faltan datos'}), 400

    from werkzeug.security import generate_password_hash
    hashed = generate_password_hash(new_password)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET PasswordHash = ? WHERE Username = ?", (hashed, username))
        conn.commit()
        return jsonify({'success': True, 'message': f'Contraseña de {username} actualizada'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


# ============================================================
#  CHAT API — Punto de entrada principal
# ============================================================
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Procesa un mensaje del usuario y devuelve la respuesta apropiada."""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    action = data.get('action', '').strip()

    if action:
        return handle_action(action, user_message)

    # Si no hay acción específica, usar el asistente AI
    return handle_ai_query(user_message)


# ============================================================
#  ACCIONES DEL BOT DBA (main.py)
# ============================================================
def handle_action(action, extra_data=''):
    """Maneja las acciones del menú, equivalentes a los botones del bot."""
    levels = {'superadmin': 4, 'admin': 3, 'dba': 2, 'monitor': 1}
    user_role = str(session.get('role', 'Monitor')).strip().lower()
    user_level = levels.get(user_role, 1)
    
    # Monitor solo puede ver: status, cpu, discos
    monitor_actions = ['status', 'cpu', 'discos']
    
    if action not in monitor_actions and user_level < 2:
        return jsonify({
            'type': 'error', 
            'message': f'❌ Acceso denegado. La acción **{action}** requiere rol DBA o superior.'
        }), 403

    handlers = {
        'status': action_status,
        'bloqueos': action_bloqueos,
        'cpu': action_cpu,
        'whoisactive': action_whoisactive,
        'discos': action_discos,
        'datalog': action_datalog,
        'tempdb': action_tempdb,
        'performance': action_performance,
        'soporte': lambda: action_soporte(extra_data),
        'cancelar': lambda: action_cancelar(extra_data),
    }

    handler = handlers.get(action)
    if handler:
        try:
            result = handler()
            return jsonify(result)
        except Exception as e:
            logging.error(f"Error en acción {action}: {e}")
            return jsonify({'type': 'error', 'message': f'❌ Error: {str(e)}'}), 500
    return jsonify({'type': 'error', 'message': '❌ Acción no reconocida'}), 400


def action_status():
    """Verifica el estado de SQL Server y retorna el nombre del servidor."""
    conn = get_active_conn()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT @@SERVERNAME")
            server_name = cursor.fetchone()[0]
            conn.close()
            return {
                'type': 'success', 
                'message': f'✅ El servicio de SQL Server (**{server_name}**) está **en línea**.'
            }
        except Exception as e:
            return {'type': 'error', 'message': f'❌ Error al consultar servidor: {str(e)}'}
    return {'type': 'error', 'message': '❌ El servicio de SQL Server **no está disponible**.'}


def action_bloqueos():
    """Consulta bloqueos recientes."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 5 
                login_name, session_id, LEFT(text, 100) AS query_preview,
                total_elapsed_time / 1000 AS segundos_ejecucion, Fecha
            FROM DataCheck.dbo.Deadlocks_Tab
            ORDER BY Fecha DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {'type': 'success', 'message': '✅ No se encontraron bloqueos recientes.'}

        bloqueos = []
        for row in rows:
            bloqueos.append({
                'usuario': str(row[0]),
                'sesion': str(row[1]),
                'query': str(row[2]),
                'segundos': str(row[3]),
                'fecha': str(row[4])
            })
        return {'type': 'table', 'title': '🔒 Últimos bloqueos detectados', 'data': bloqueos}
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error al consultar bloqueos: {str(e)}'}


def action_cpu():
    """Obtiene información de CPU y memoria directamente desde SQL Server."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos para métricas.'}

    try:
        cursor = conn.cursor()
        
        # 1. Obtener uso de CPU (Promedio del último minuto desde Ring Buffers)
        cpu_query = """
            SELECT TOP 1 
                [SQLProcessUtilization] AS [CPU]
            FROM (
                SELECT 
                    record.value('(./Record/@id)[1]', 'int') AS record_id,
                    record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS [SQLProcessUtilization]
                FROM (
                    SELECT CAST(record AS xml) AS [record] 
                    FROM sys.dm_os_ring_buffers 
                    WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR'
                    AND record LIKE '%<SchedulerMonitorEvent>%'
                ) AS x
            ) AS y 
            ORDER BY record_id DESC
        """
        cursor.execute(cpu_query)
        cpu_row = cursor.fetchone()
        cpu_percent = cpu_row[0] if cpu_row else 0

        # 2. Obtener uso de Memoria
        mem_query = """
            SELECT 
                total_physical_memory_kb / 1024 / 1024 AS total_gb,
                available_physical_memory_kb / 1024 / 1024 AS available_gb,
                system_memory_state_desc
            FROM sys.dm_os_sys_memory
        """
        cursor.execute(mem_query)
        mem_row = cursor.fetchone()
        
        if mem_row:
            total_gb = round(float(mem_row[0]), 1)
            avail_gb = round(float(mem_row[1]), 1)
            used_gb = round(total_gb - avail_gb, 1)
            mem_percent = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0
        else:
            total_gb, used_gb, mem_percent = 0, 0, 0

        # 3. Obtener núcleos e hilos (sys.dm_os_sys_info)
        info_query = "SELECT cpu_count, hyperthread_ratio FROM sys.dm_os_sys_info"
        cursor.execute(info_query)
        info_row = cursor.fetchone()
        cpu_cores = info_row[0] / info_row[1] if info_row else 'N/A'
        cpu_threads = info_row[0] if info_row else 'N/A'

        conn.close()

        return {
            'type': 'metrics',
            'title': '⚙️ Recursos de la Instancia SQL',
            'data': {
                'cpu_percent': cpu_percent,
                'cpu_cores': cpu_cores,
                'cpu_threads': cpu_threads,
                'mem_percent': mem_percent,
                'mem_total_gb': total_gb,
                'mem_used_gb': used_gb
            }
        }
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error en métricas remotas: {e}")
        return {'type': 'error', 'message': f'❌ No se pudieron obtener métricas: {str(e)}'}


def action_whoisactive():
    """Ejecuta sp_whoisactive para ver sesiones activas con detalle completo."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        # get_outer_command=2 trae el SQL completo.
        cursor.execute("EXEC sp_whoisactive @get_outer_command = 2, @get_task_info = 2")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return {'type': 'success', 'message': '📌 No hay sesiones activas significativas en este momento.'}

        sesiones = []
        for row in rows:
            # Crear un diccionario para acceder por nombre de columna (case-insensitive)
            raw_data = {col.lower(): row[i] for i, col in enumerate(columns)}
            
            # Extraer sql_text (limpieza de XML si es necesario)
            sql_raw = raw_data.get('sql_text') or raw_data.get('[sql_text]')
            if sql_raw and hasattr(sql_raw, '__str__'):
                sql_str = str(sql_raw)
                # Si viene envuelto en XML de sp_whoisactive, intentar extraer lo que está entre tags o simplemente limpiar
                if '<?query' in sql_str:
                    match = re.search(r'--\s*(.*)', sql_str, re.DOTALL)
                    if match: sql_str = match.group(1)
                sql_final = sql_str[:500] + ('...' if len(sql_str) > 500 else '')
            else:
                sql_final = "N/A"

            # Duración: sp_whoisactive usa [dd hh:mm:ss.ms]
            duration = raw_data.get('dd hh:mm:ss.ms') or raw_data.get('[dd hh:mm:ss.ms]') or "0s"
            
            # Mapeo amigable
            sesiones.append({
                'sesion_id': str(raw_data.get('session_id', 'N/A')),
                'usuario': str(raw_data.get('login_name', 'N/A')),
                'db': str(raw_data.get('database_name', 'N/A')),
                'duracion': str(duration),
                'bloquea_spid': str(raw_data.get('blocking_session_id', '') or ''),
                'wait': str(raw_data.get('wait_info', 'Runnable')),
                'query': str(sql_final)
            })
        
        return {
            'type': 'table', 
            'title': '👤 Sesiones Activas Detalladas', 
            'data': sesiones,
            'columns': ['sesion_id', 'usuario', 'db', 'duracion', 'bloquea_spid', 'wait', 'query']
        }
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error en sp_whoisactive: {e}")
        return {'type': 'error', 'message': f'❌ Error al ejecutar sp_whoisactive: {str(e)}'}


def action_discos():
    """Información de espacio en disco."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.sp_DiskSpace")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return {'type': 'success', 'message': 'No se encontró información de espacio en disco.'}

        discos = []
        for row in rows:
            disco = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, float):
                    val = round(val, 2)
                disco[col] = str(val)
            discos.append(disco)
        return {'type': 'table', 'title': '💾 Espacio en Discos', 'data': discos}
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error: {str(e)}'}


def action_datalog():
    """Consulta tamaños de Data y Log."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        cursor.execute("EXEC sp_GetDatabaseSizes")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()

        if not rows:
            return {'type': 'success', 'message': 'No se encontró información.'}

        datos = []
        for row in rows:
            item = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, float):
                    val = round(val, 2)
                item[col] = str(val)
            datos.append(item)
        return {'type': 'table', 'title': '🕵️‍♂️ Data y Log', 'data': datos}
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error: {str(e)}'}


def action_tempdb():
    """Muestra estado de TempDB."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, physical_name, size * 8 / 1024 AS sizeMB
            FROM sys.master_files
            WHERE database_id = DB_ID('tempdb')
        """)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return {'type': 'success', 'message': 'No se encontró información de TempDB.'}

        total_mb = sum(row[2] for row in rows)
        archivos = []
        for row in rows:
            archivos.append({
                'nombre': str(row[0]),
                'ruta': str(row[1]),
                'tamaño_mb': str(row[2])
            })
        return {
            'type': 'table',
            'title': f'🧹 TempDB — Total: {total_mb} MB',
            'data': archivos
        }
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error: {str(e)}'}


def action_performance():
    """Verifica performance general del servidor remoto de SQL."""
    conn = get_active_conn()
    if not conn:
        return {'type': 'error', 'message': '❌ No se pudo conectar al servidor para verificar performance.'}

    try:
        cursor = conn.cursor()
        
        # 1. Nombre del Servidor y Estado
        cursor.execute("SELECT @@SERVERNAME")
        server_name = cursor.fetchone()[0]

        # 2. CPU Remote (SQL)
        cpu_query = """
            SELECT TOP 1 [SQLProcessUtilization] FROM (
                SELECT record.value('(./Record/SchedulerMonitorEvent/SystemHealth/ProcessUtilization)[1]', 'int') AS [SQLProcessUtilization],
                record.value('(./Record/@id)[1]', 'int') AS record_id
                FROM (SELECT CAST(record AS xml) AS [record] FROM sys.dm_os_ring_buffers 
                WHERE ring_buffer_type = N'RING_BUFFER_SCHEDULER_MONITOR' AND record LIKE '%<SchedulerMonitorEvent>%') AS x
            ) AS y ORDER BY record_id DESC
        """
        cursor.execute(cpu_query)
        cpu_row = cursor.fetchone()
        cpu_val = cpu_row[0] if cpu_row else "N/A"

        # 3. Memoria Remote (SQL)
        mem_query = """
            SELECT total_physical_memory_kb/1024/1024, available_physical_memory_kb/1024/1024 
            FROM sys.dm_os_sys_memory
        """
        cursor.execute(mem_query)
        mem_row = cursor.fetchone()
        if mem_row:
            total_gb = round(float(mem_row[0]), 1)
            avail_gb = round(float(mem_row[1]), 1)
            used_gb = round(total_gb - avail_gb, 1)
            mem_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0
            mem_info = f"{mem_pct}% usada ({used_gb} / {total_gb} GB)"
        else:
            mem_info = "N/A"

        # 4. Discos (vía sp_DiskSpace si existe)
        disk_summary = ""
        try:
            cursor.execute("EXEC dbo.sp_DiskSpace")
            d_rows = cursor.fetchall()
            if d_rows:
                disk_summary = "\n".join([f"  • {row[0]}: {row[2]} GB libres / {row[1]} GB total" for row in d_rows])
        except Exception:
            disk_summary = "  • Información de discos no disponible."

        conn.close()

        message = (
            f"**📈 Performance de la Instancia: {server_name}**\n\n"
            f"**Estado:** ✅ En línea\n"
            f"**CPU (SQL/Sist.):** {cpu_val}%\n"
            f"**Memoria:** {mem_info}\n"
            f"**Discos Remotos:**\n{disk_summary}"
        )
        return {'type': 'success', 'message': message}
    except Exception as e:
        if conn: conn.close()
        return {'type': 'error', 'message': f'❌ Error al obtener performance: {str(e)}'}


def action_soporte(mensaje):
    """Registra una solicitud de soporte."""
    if not mensaje:
        return {'type': 'prompt', 'message': '📝 Por favor, describe tu solicitud de soporte:'}

    conn = get_db_connection()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        username = session.get('username', 'web_user')
        cursor.execute("""
            INSERT INTO tickets 
            (telegram_id, mensaje, fecha, prioridad, categoria, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, mensaje, datetime.now(), 'Media', 'General', 'Pendiente'))
        conn.commit()
        conn.close()
        return {'type': 'success', 'message': '✅ Tu solicitud de soporte ha sido registrada y será atendida pronto.'}
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error al registrar solicitud: {str(e)}'}


def action_cancelar(spid_str):
    """Cancela una consulta SQL por SPID."""
    if not spid_str:
        return {'type': 'prompt', 'message': '⚠️ Por favor, ingresa el SPID de la consulta a cancelar:', 'input_action': 'cancelar'}

    try:
        spid = int(spid_str)
    except ValueError:
        return {'type': 'error', 'message': '⚠️ El SPID debe ser un número entero válido.'}

    conn = get_db_connection()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        cursor.execute(f"KILL {spid}")
        conn.close()
        return {'type': 'success', 'message': f'✅ Consulta con SPID {spid} cancelada correctamente.'}
    except Exception as e:
        conn.close()
        return {'type': 'error', 'message': f'❌ Error al cancelar SPID {spid}: {str(e)}'}


# ============================================================
#  ASISTENTE SQL AI (bot_sql_ai.py)
# ============================================================
def es_error_sql(texto):
    return bool(re.search(r'error|msg\s+\d+|invalid|cannot|timeout|deadlock|provider|\.database\.', texto, re.I))


def es_pregunta_sql(texto):
    return bool(re.search(r'\?|cómo|explica|ejemplo|diferencia|join|group by|where|select|create|usuario|primary key|oracle|tamaño', texto, re.I))


def handle_ai_query(texto):
    """Procesa preguntas o errores SQL con Gemini → BD → Web."""
    if not texto:
        return jsonify({'type': 'info', 'message': '💡 Escribe un error SQL o una pregunta sobre bases de datos, o usa los botones del menú.'})

    es_error = es_error_sql(texto)
    es_pregunta = es_pregunta_sql(texto)

    if not (es_error or es_pregunta):
        return jsonify({'type': 'info', 'message': '💡 No reconozco un error o pregunta SQL. Intenta escribir un error de SQL Server o una pregunta sobre bases de datos, o usa los botones del menú.'})

    # 1. Buscar en BD
    respuesta_bd = buscar_en_historial(texto)
    if respuesta_bd:
        return jsonify({'type': 'ai', 'message': respuesta_bd, 'source': 'Historial'})

    # 2. Gemini AI
    if GEMINI_AVAILABLE:
        try:
            prompt = (f"Error SQL: {texto}\nSolución paso a paso en español, solo texto plano."
                      if es_error else
                      f"Pregunta SQL: {texto}\nExplica con ejemplo en español, solo texto plano.")
            response = gemini_model.generate_content(prompt)
            if response and response.text:
                respuesta = response.text.strip()
                respuesta = re.sub(r'([*_`])', '', respuesta)
                respuesta = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', respuesta)
                if len(respuesta) > 3800:
                    respuesta = respuesta[:3750] + "\n\n... (respuesta truncada)"
                guardar_en_historial(session.get('username', 'web'), texto, respuesta, es_error, 'Gemini')
                return jsonify({'type': 'ai', 'message': respuesta, 'source': 'Gemini AI'})
        except Exception as e:
            logging.error(f"Gemini error: {e}")

    # 3. DuckDuckGo fallback
    if DDGS_AVAILABLE:
        try:
            query = f'"{texto[:80]}" SQL Server solución' if es_error else f'"{texto}" SQL tutorial'
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=2))
            if resultados:
                contexto = "\n".join([f"{i+1}. {r['title']}\n{r['body'][:140]}..." for i, r in enumerate(resultados)])
                respuesta = f"Resultados para: {query}\n\n{contexto}"
                guardar_en_historial(session.get('username', 'web'), texto, respuesta, es_error, 'Web')
                return jsonify({'type': 'ai', 'message': respuesta, 'source': 'Búsqueda Web'})
        except Exception as e:
            logging.error(f"DuckDuckGo error: {e}")

    return jsonify({'type': 'info', 'message': '⚠️ No pude encontrar una respuesta. Intenta reformular tu pregunta.'})


def buscar_en_historial(pregunta):
    """Busca en el historial de consultas AI."""
    conn = get_db_connection(use_ai_db=True)
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT TOP 1 Respuesta FROM HistorialConsultas
            WHERE Pregunta LIKE ? OR ? LIKE CONCAT('%', Pregunta, '%')
            ORDER BY Id DESC
        """, f'%{pregunta[:50]}%', pregunta[:50])
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        conn.close()
        return None


def guardar_en_historial(usuario, pregunta, respuesta, es_error, fuente):
    """Guarda en el historial de consultas AI."""
    conn = get_db_connection(use_ai_db=True)
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO HistorialConsultas (Usuario, Pregunta, Respuesta, EsError, Fuente)
            VALUES (?, ?, ?, ?, ?)
        """, usuario, pregunta, respuesta, es_error, fuente)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error guardando historial: {e}")
        conn.close()


# ============================================================
#  MAIN
# ============================================================
if __name__ == '__main__':
    logging.info("DataCheck Web - Iniciando servidor...")
    app.run(debug=True, host='0.0.0.0', port=5001)
