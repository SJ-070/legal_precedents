"""
Gemini API Configuration
환경변수 및 Gemini API 설정
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 환경 변수 로드
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Gemini API 클라이언트 초기화
client = genai.Client(api_key=GOOGLE_API_KEY)
