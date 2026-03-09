import sys
import os
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.config import AI_CONN_STR, CONN_STR, GEMINI_API_KEY
import pyodbc

logging.basicConfig(level=logging.INFO)

def test_db_ai():
    print(f"Testing AI DB Connection: {AI_CONN_STR}")
    try:
        conn = pyodbc.connect(AI_CONN_STR, timeout=5)
        print("✅ AI DB Connected!")
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 * FROM HistorialConsultas")
        row = cursor.fetchone()
        print(f"AI DB Data Sample: {row}")
        conn.close()
    except Exception as e:
        print(f"❌ AI DB Error: {e}")

def test_gemini():
    print(f"Testing Gemini API Key: {GEMINI_API_KEY[:10]}...")
    import google.generativeai as genai
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        resp = model.generate_content("Hola, di 'test'")
        print(f"✅ Gemini Response: {resp.text}")
    except Exception as e:
        print(f"❌ Gemini Error: {e}")

if __name__ == "__main__":
    test_db_ai()
    print("-" * 20)
    test_gemini()
