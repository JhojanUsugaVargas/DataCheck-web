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
        prioridad = 'Media'
        
        cursor.execute("""
            INSERT INTO tickets 
            (user_id, mensaje, fecha, prioridad, categoria, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (username, mensaje, datetime.now(), prioridad, 'General', 'Pendiente'))
        conn.commit()
        conn.close()

        # Resumen para el usuario
        resumen = mensaje[:100] + ('...' if len(mensaje) > 100 else '')
        msg = (
            f"✅ **Solicitud de soporte registrada**\n\n"
            f"**Resumen:** {resumen}\n"
            f"**Prioridad:** {prioridad}\n\n"
            "Será atendida por nuestro equipo pronto."
        )
        return {'type': 'success', 'message': msg}
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error al registrar solicitud: {e}")
        return {'type': 'error', 'message': f'❌ Error al registrar solicitud: {str(e)}'}
