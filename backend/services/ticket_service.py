from datetime import datetime
from flask import session
import logging
from utils.config import get_db_connection

def action_soporte(mensaje):
    """Registra una solicitud de soporte."""
    if not mensaje:
        return {'type': 'prompt', 'message': '📝 Por favor, describe tu solicitud de soporte:', 'input_action': 'soporte'}

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
        if conn: conn.close()
        logging.error(f"Error al registrar solicitud: {e}")
        return {'type': 'error', 'message': f'❌ Error al registrar solicitud: {str(e)}'}
