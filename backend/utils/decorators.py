from functools import wraps
from flask import session, redirect, url_for, request, jsonify

def login_required(f):
    """Decorador para proteger rutas que requieren autenticación."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado', 'redirect': '/login'}), 401
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """Decorador para proteger rutas por rol (Admin, DBA, Monitor)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('logged_in'):
                # The login route is now in the 'auth' blueprint
                return redirect(url_for('auth.login_page'))
            
            levels = {
                'administrador': 3,
                'admin': 3,
                'dba': 2,
                'monitoreo': 1,
                'monitor': 1
            }
            user_role = str(session.get('role', 'Monitoreo')).strip().lower()
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
