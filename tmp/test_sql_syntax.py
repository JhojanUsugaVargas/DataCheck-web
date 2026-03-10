import sys
import os
import pyodbc

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.config import AI_CONN_STR

def test_history_query():
    print(f"Testing query on: {AI_CONN_STR}")
    pregunta = "¿Cómo va todo?"
    try:
        conn = pyodbc.connect(AI_CONN_STR, timeout=5)
        cursor = conn.cursor()
        
        # Exact query from ai_service.py
        sql = """
            SELECT TOP 1 Respuesta FROM HistorialConsultas
            WHERE Pregunta LIKE ? OR ? LIKE CONCAT('%', Pregunta, '%')
            ORDER BY Id DESC
        """
        print("Ejecutando consulta...")
        cursor.execute(sql, f'%{pregunta[:50]}%', pregunta[:50])
        row = cursor.fetchone()
        print(f"Resultado: {row}")
        conn.close()
    except Exception as e:
        print(f"❌ Error detectado: {e}")

if __name__ == "__main__":
    test_history_query()
