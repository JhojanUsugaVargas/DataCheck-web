"""
Autenticación y gestión de sesiones para DataCheck Web utilizando la base de datos.
"""
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import check_password_hash
import pyotp
from config import get_db_connection

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado', 'redirect': '/login'}), 401
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorador para proteger rutas por rol (Admin, DBA, Monitor)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                return redirect(url_for('login_page'))
            
            levels = {
                'administrador': 4,
                'superadmin': 4,
                'admin': 3,
                'dba': 2,
                'monitor': 1,
                'monitoreo': 1
            }
            user_role = str(session.get('role', 'Monitor')).strip().lower()
            required_role_clean = required_role.strip().lower()
            
            user_level = levels.get(user_role, 1)
            required_level = levels.get(required_role_clean, 1)
            
            if user_level < required_level:
                return jsonify({
                    'error': 'Acceso denegado', 
                    'message': f'La acción requiere nivel {required_level}, pero tienes {user_role} (Nivel {user_level}).'
                }), 403
                 
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def authenticate(username, password):
    """Verifica credenciales del usuario en la base de datos."""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT PasswordHash, Role, FullName, MFAEnabled, MFASecret FROM Users WHERE Username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            return None
            
        stored_hash = row[0]
        if check_password_hash(stored_hash, password):
            return {
                'username': username,
                'role': row[1],
                'full_name': row[2],
                'mfa_enabled': bool(row[3]),
                'mfa_secret': row[4]
            }
        return None
    except Exception as e:
        print(f"Error en autenticación: {e}")
        return None
    finally:
        conn.close()

def generate_mfa_secret():
    """Genera un nuevo secreto TOTP."""
    return pyotp.random_base32()

def verify_mfa_token(secret, token):
    """Verifica si un token TOTP es válido para un secreto dado."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token)
