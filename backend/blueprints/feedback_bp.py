
from flask import Blueprint, request, jsonify, session
from utils.decorators import login_required
from utils.config import get_db_connection
import logging

feedback_bp = Blueprint('feedback', __name__)

@feedback_bp.route('/api/feedback', methods=['POST'])
@login_required
def submit_feedback():
    data = request.get_json()
    rating = data.get('rating')
    suggestion = data.get('suggestion', '').strip()
    user_id = session.get('user_id')

    if not rating:
        return jsonify({'success': False, 'message': 'Se requiere una calificación.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Error de conexión con la base de datos.'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO UserFeedback (UserID, Rating, Suggestion)
            VALUES (?, ?, ?)
        """, (user_id, rating, suggestion))
        conn.commit()
        return jsonify({'success': True, 'message': '¡Gracias por tu feedback! Tus sugerencias nos ayudan a mejorar.'})
    except Exception as e:
        logging.error(f"Error al guardar feedback: {str(e)}")
        return jsonify({'success': False, 'message': 'Ocurrió un error al procesar tu feedback.'}), 500
    finally:
        conn.close()
