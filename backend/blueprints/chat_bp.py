from flask import Blueprint, request, jsonify, session
from services.ai_service import get_ai_response
from services.ticket_service import action_soporte
from utils.decorators import login_required
import logging

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Procesa un mensaje del usuario y devuelve la respuesta apropiada."""
    data = request.get_json()
    user_message = data.get('message', '')
    if isinstance(user_message, str):
        user_message = user_message.strip()
    action = data.get('action', '').strip()

    if not action:
        # Detección de palabras clave para acciones rápidas
        msg_low = user_message.lower() if isinstance(user_message, str) else ""
        if "compactar tempdb" in msg_low or "shrink tempdb" in msg_low:
            action = "tempdb_shrink"

    if action:
        return handle_action_dispatcher(action, user_message)

    # Si no hay acción específica, usar el asistente AI
    username = session.get('username', 'web')
    response = get_ai_response(user_message, username)
    return jsonify(response)

def handle_action_dispatcher(action, extra_data=''):
    """Despacha las acciones a los servicios o funciones correspondientes."""
    
    # Especial: Soporte (Anomalías)
    if action == 'soporte':
        result = action_soporte(extra_data)
        return jsonify(result)
    
    # Otras acciones se manejan vía redirección interna o llamada a dba_bp (simulado aquí por ahora)
    # En una implementación real, dispararíamos las funciones de dba_bp directamente o vía API interna.
    # Para mantener simplicidad, el dispatcher sabe qué acción llamar.
    
    from blueprints.dba_bp import (
        action_status, action_bloqueos, action_cpu, action_whoisactive, 
        action_discos, action_tempdb, action_performance, action_datalog, 
        action_cancelar, action_tempdb_shrink, action_jobs, action_alwayson, action_databases, action_backups
    )
    
    handlers = {
        'status': lambda: action_status().get_json(),
        'bloqueos': lambda: action_bloqueos().get_json(),
        'cpu': lambda: action_cpu().get_json(),
        'whoisactive': lambda: action_whoisactive().get_json(),
        'discos': lambda: action_discos().get_json(),
        'tempdb': lambda: action_tempdb().get_json(),
        'tempdb_shrink': lambda: action_tempdb_shrink().get_json(),
        'performance': lambda: action_performance().get_json(),
        'datalog': lambda: action_datalog().get_json(),
        'cancelar': lambda: action_cancelar().get_json(),
        'jobs': lambda: action_jobs().get_json(),
        'alwayson': lambda: action_alwayson().get_json(),
        'databases': lambda: action_databases().get_json(),
        'backups': lambda: action_backups().get_json(),
    }
    
    handler = handlers.get(action)
    if handler:
        try:
            return jsonify(handler())
        except Exception as e:
            logging.error(f"Error en dispatcher {action}: {e}")
            return jsonify({'type': 'error', 'message': f'❌ Error: {str(e)}'}), 500
            
    return jsonify({'type': 'error', 'message': '❌ Acción no reconocida'}), 400
