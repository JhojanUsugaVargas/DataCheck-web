from datetime import datetime
from flask import session
import logging
from utils.config import get_db_connection

def action_soporte(data):
    """Registra una solicitud de soporte estructurada."""
    if not data or not isinstance(data, dict):
        return {'type': 'prompt', 'message': '📝 Por favor, describe tu solicitud de soporte:', 'input_action': 'soporte'}

    mensaje = data.get('mensaje')
    if not mensaje:
        return {'type': 'error', 'message': '❌ El mensaje es obligatorio.'}

    conn = get_db_connection()
    if not conn:
        return {'type': 'error', 'message': '❌ Error al conectar a la base de datos.'}

    try:
        cursor = conn.cursor()
        user_id = session.get('user_id')
        if not user_id:
            # Fallback a buscar por username si no está en sesión (aunque debería estar)
            username = session.get('username', 'web_user')
            cursor.execute("SELECT user_id FROM Users WHERE Username = ?", (username,))
            row = cursor.fetchone()
            user_id = row[0] if row else 1 # ID por defecto si falla todo

        tipo = data.get('tipo', 'Incidente')
        modulo = data.get('modulo', 'General')
        impacto = data.get('impacto', 'Medio')
        prioridad = data.get('prioridad', 'Alta')
        estado = 'Abierto'
        fecha_reporte = datetime.now()
        
        cursor.execute("""
            INSERT INTO tickets 
            (user_id, mensaje, tipo, modulo, impacto, prioridad, estado, fecha_reporte)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, mensaje, tipo, modulo, impacto, prioridad, estado, fecha_reporte))
        conn.commit()
        conn.close()

        # Resumen para el usuario
        resumen = mensaje[:100] + ('...' if len(mensaje) > 100 else '')
        msg = (
            f"✅ **Solicitud de soporte registrada**\n\n"
            f"**Tipo:** {tipo}\n"
            f"**Módulo:** {modulo}\n"
            f"**Prioridad:** {prioridad}\n"
            f"**Resumen:** {resumen}\n\n"
            "Será atendida por nuestro equipo pronto."
        )
        return {'type': 'success', 'message': msg}
    except Exception as e:
        if conn: conn.close()
        logging.error(f"Error al registrar solicitud: {e}")
        return {'type': 'error', 'message': f'❌ Error al registrar solicitud: {str(e)}'}
