import os
import re
import logging
from datetime import datetime
from utils.config import GEMINI_API_KEY, get_db_connection
import google.generativeai as genai
from duckduckgo_search import DDGS

# Configurar Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Usar gemini-2.0-flash que es la versión más reciente disponible
    ai_model = genai.GenerativeModel('gemini-2.0-flash')
    GEMINI_AVAILABLE = True
except Exception as e:
    logging.error(f"Error crítico configurando Gemini: {e}")
    GEMINI_AVAILABLE = False

# Configurar DuckDuckGo
try:
    DDGS_AVAILABLE = True
except Exception:
    DDGS_AVAILABLE = False

def es_error_sql(texto):
    return bool(re.search(r'error|msg\s+\d+|invalid|cannot|timeout|deadlock|provider|\.database\.', texto, re.I))

def es_pregunta_sql(texto):
    return bool(re.search(r'\?|cómo|explica|ejemplo|diferencia|join|group by|where|select|create|usuario|primary key|oracle|tamaño', texto, re.I))

def buscar_en_historial(pregunta):
    """Busca en el historial de consultas AI."""
    from utils.config import get_db_connection
    conn = get_db_connection(use_ai_db=True)
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Respuesta] FROM [HistorialConsultas] WHERE [Pregunta] LIKE ? OR ? LIKE '%' + [Pregunta] + '%' ORDER BY [Id] DESC", 
                       f'%{pregunta[:50]}%', pregunta[:50])
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        if conn: conn.close()
        return None

def guardar_en_historial(usuario, pregunta, respuesta, es_error, fuente):
    """Guarda en el historial de consultas AI."""
    from utils.config import get_db_connection
    conn = get_db_connection(use_ai_db=True)
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO [HistorialConsultas] ([Usuario], [Pregunta], [Respuesta], [EsError], [Fuente]) VALUES (?, ?, ?, ?, ?)",
                       usuario, pregunta, respuesta, es_error, fuente)
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"Error guardando historial: {e}")
        if conn: conn.close()

def get_ai_response(texto, username):
    """Procesa preguntas o errores SQL con Gemini → BD → Web."""
    try:
        if not texto or not isinstance(texto, str):
            if isinstance(texto, dict):
                # Si recibimos un diccionario (como el de soporte), intentamos extraer el mensaje
                texto = texto.get('mensaje', '')
            
            if not texto or not isinstance(texto, str):
                return {'type': 'info', 'message': '💡 Escribe un error SQL o una pregunta sobre bases de datos.'}

        es_error = es_error_sql(texto)
        es_pregunta = es_pregunta_sql(texto)

        if not (es_error or es_pregunta):
            return {'type': 'info', 'message': '💡 No reconozco un error o pregunta SQL.'}

        # 1. Buscar en BD
        respuesta_bd = buscar_en_historial(texto)
        if respuesta_bd:
            return {'type': 'ai', 'message': respuesta_bd, 'source': 'Historial'}

        # 2. Gemini AI
        if GEMINI_AVAILABLE:
            try:
                prompt = (f"Error SQL: {texto}\nSolución paso a paso en español, solo texto plano."
                          if es_error else
                          f"Pregunta SQL: {texto}\nExplica con ejemplo en español, solo texto plano.")
                response = ai_model.generate_content(prompt)
                if response and response.text:
                    respuesta = response.text.strip()
                    respuesta = re.sub(r'([*_`])', '', respuesta)
                    respuesta = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', respuesta)
                    if len(respuesta) > 3800:
                        respuesta = respuesta[:3750] + "\n\n... (respuesta truncada)"
                    guardar_en_historial(username, texto, respuesta, es_error, 'Gemini')
                    return {'type': 'ai', 'message': respuesta, 'source': 'Gemini AI'}
            except Exception as e:
                logging.error(f"Gemini error: {e}")

        # 3. DuckDuckGo fallback
        if DDGS_AVAILABLE:
            try:
                query = f'"{texto[:80]}" SQL Server solución' if es_error else f'"{texto}" SQL tutorial'
                with DDGS() as ddgs:
                    resultados = list(ddgs.text(query, max_results=2))
                if resultados:
                    contexto = "\n".join([f"{i+1}. {r['title']}\n{r['body'][:140]}..." for i, r in enumerate(resultados)])
                    respuesta = f"Resultados para: {query}\n\n{contexto}"
                    guardar_en_historial(username, texto, respuesta, es_error, 'Web')
                    return {'type': 'ai', 'message': respuesta, 'source': 'Búsqueda Web'}
            except Exception as e:
                logging.error(f"DuckDuckGo error: {e}")

        return {'type': 'info', 'message': '⚠️ No pude encontrar una respuesta procesable en este momento.'}
    except Exception as e:
        logging.error(f"Error global en get_ai_response: {e}")
        return {'type': 'error', 'message': f'❌ Error interno al procesar la consulta AI: {str(e)}'}
