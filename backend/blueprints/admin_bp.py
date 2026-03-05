from flask import Blueprint, request, jsonify, session
from utils.decorators import login_required, role_required
from utils.config import get_db_connection

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/users', methods=['GET'])
@login_required
@role_required('Administrador')
def get_users():
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'Error de conexión'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT Username, FullName, Role, CreatedAt, IsActive, MFAEnabled FROM Users")
        users = []
        for row in cursor.fetchall():
            users.append({
                'username': row[0],
                'full_name': row[1],
                'role': row[2],
                'created_at': str(row[3]),
                'is_active': bool(row[4]),
                'mfa_enabled': bool(row[5])
            })
        return jsonify(users)
    finally:
        conn.close()

@admin_bp.route('/api/admin/users/add', methods=['POST'])
@login_required
@role_required('Administrador')
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

@admin_bp.route('/api/admin/users/reset_password', methods=['POST'])
@login_required
@role_required('Administrador')
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

@admin_bp.route('/api/admin/users/rename', methods=['POST'])
@login_required
@role_required('Administrador')
def rename_user():
    data = request.get_json()
    old_username = data.get('old_username')
    new_username = data.get('new_username')

    if not old_username or not new_username:
        return jsonify({'error': 'Faltan datos'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET Username = ? WHERE Username = ?", (new_username, old_username))
        conn.commit()
        return jsonify({'success': True, 'message': f'Usuario renombrado de {old_username} a {new_username}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/admin/users/toggle_status', methods=['POST'])
@login_required
@role_required('Administrador')
def toggle_user_status():
    data = request.get_json()
    username = data.get('username')
    is_active = data.get('is_active')

    if username is None or is_active is None:
        return jsonify({'error': 'Faltan datos'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE Users SET IsActive = ? WHERE Username = ?", (1 if is_active else 0, username))
        conn.commit()
        status_text = "activado" if is_active else "inactivado"
        return jsonify({'success': True, 'message': f'Usuario {username} {status_text}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/admin/users/delete', methods=['DELETE'])
@login_required
@role_required('Administrador')
def delete_user():
    username = request.args.get('username')
    if not username:
        return jsonify({'error': 'Faltan datos'}), 400
    
    # Evitar auto-borrado
    if username == session.get('username'):
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 400

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Users WHERE Username = ?", (username,))
        conn.commit()
        return jsonify({'success': True, 'message': f'Usuario {username} eliminado'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
