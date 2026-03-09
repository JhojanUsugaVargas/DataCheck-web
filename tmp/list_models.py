import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from utils.config import GEMINI_API_KEY
import google.generativeai as genai

print(f"Using API Key: {GEMINI_API_KEY[:10]}...")
try:
    genai.configure(api_key=GEMINI_API_KEY)
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")
