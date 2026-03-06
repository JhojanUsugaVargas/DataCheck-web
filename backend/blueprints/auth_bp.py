from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from utils.auth_utils import authenticate, verify_mfa_token, generate_mfa_secret
from utils.decorators import login_required, role_required
import requests
import logging
from utils.config import RECAPTCHA_SECRET_KEY, RECAPTCHA_SITE_KEY, SECRET_KEY, get_db_connection

import os

auth_bp = Blueprint('auth', __name__)

def verify_recaptcha(response_token):
    """Verifica el token de reCAPTCHA con el servidor de Google.
    Si RECAPTCHA_ENABLED es false o RECAPTCHA_SECRET_KEY no está configurado, se omite la validación."""
    
    # Soporte para desactivación explícita (del remoto)
    if os.environ.get('RECAPTCHA_ENABLED', 'true').lower() == 'false':
        logging.warning("reCAPTCHA desactivado (RECAPTCHA_ENABLED=false)")
        return True
        
    # Si no hay key configurada (de hoy)
    if not RECAPTCHA_SECRET_KEY:
        return True
        
    if not response_token:
        return False
        
    try:
        url = "https://www.google.com/recaptcha/api/siteverify"
        payload = {
            'secret': RECAPTCHA_SECRET_KEY,
            'response': response_token
        }
        res = requests.post(url, data=payload, timeout=5)
        result = res.json()
        return result.get('success', False)
    except Exception as e:
        logging.warning(f"No se pudo verificar reCAPTCHA (error de red): {e}. Se omite la validación.")
        return True  # Fail-open

@auth_bp.route('/login')
def login_page():
    if session.get('logged_in'):
        # Combinar base url del remoto
        base = os.environ.get('APP_BASE_URL', '').rstrip('/')
        return redirect(f"{base}/")
    return render_template('login.html', site_key=RECAPTCHA_SITE_KEY)

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    recaptcha_token = data.get('recaptcha_token', '')

    if not verify_recaptcha(recaptcha_token):
        return jsonify({
            'success': False, 
            'message': 'Validación reCAPTCHA fallida. Por favor, marca "No soy un robot".'
        }), 401

    user_data = authenticate(username, password)
    
    if user_data:
        if user_data.get('mfa_enabled'):
            token = data.get('token')
            if not token:
                return jsonify({
                    'success': False, 
                    'requires_mfa': True, 
                    'message': 'Se requiere código de autenticación'
                })
            
            if not verify_mfa_token(user_data.get('mfa_secret'), token):
                return jsonify({'success': False, 'message': 'Código MFA inválido'}), 401

        session.permanent = True
        session['logged_in'] = True
        session['username'] = user_data['username']
        session['role'] = (user_data['role'] or 'Monitor').strip()
        session['full_name'] = user_data['full_name']
        session['user_id'] = user_data['user_id']
        return jsonify({'success': True, 'message': f'¡Bienvenido, {user_data["full_name"]}!'})
    
    return jsonify({'success': False, 'message': 'Credenciales incorrectas'}), 401

@auth_bp.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/api/profile/update', methods=['POST'])
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
            if session.get('role') not in ['Administrador', 'Admin']:
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

@auth_bp.route('/api/mfa/setup', methods=['GET'])
@login_required
def mfa_setup():
    username = session.get('username')
    secret = generate_mfa_secret()
    session['temp_mfa_secret'] = secret
    
    import pyotp
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=username, issuer_name="DataCheck Web")
    
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

@auth_bp.route('/api/mfa/activate', methods=['POST'])
@login_required
def mfa_activate():
    data = request.get_json()
    token = data.get('token')
    secret = session.get('temp_mfa_secret')
    username = session.get('username')
    
    if not secret or not token:
        return jsonify({'success': False, 'error': 'Datos faltantes'}), 400
        
    if verify_mfa_token(secret, token):
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

@auth_bp.route('/api/profile/photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({'error': 'No se encontró el archivo'}), 400
    
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'error': 'Archivo sin nombre'}), 400
    
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

@auth_bp.route('/api/profile/photo/<username>')
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
