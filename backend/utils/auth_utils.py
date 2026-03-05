"""
Autenticación y gestión de sesiones para DataCheck Web utilizando la base de datos.
"""
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
from werkzeug.security import check_password_hash
import pyotp
from utils.config import get_db_connection

def authenticate(username, password):
    """Verifica credenciales del usuario en la base de datos."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT UserId, Username, PasswordHash, Role, FullName, MFAEnabled, MFASecret, IsActive FROM Users WHERE Username = ?", (username,))
        row = cursor.fetchone()
        if row and check_password_hash(row[2], password):
            is_active = row[7] if len(row) > 7 else 1  # Default to 1 if not yet present
            if not is_active:
                return None # Account inactive
            
            return {
                'user_id': row[0],
                'username': row[1],
                'role': row[3],
                'full_name': row[4],
                'mfa_enabled': row[5],
                'mfa_secret': row[6]
            }
        return None
    finally:
        conn.close()

def generate_mfa_secret():
    """Genera un nuevo secreto base32 para MFA."""
    return pyotp.random_base32()

def verify_mfa_token(secret, token):
    """Verifica si un token TOTP es válido para un secreto dado."""
    if not secret or not token: return False
    totp = pyotp.TOTP(secret)
    return totp.verify(token)
