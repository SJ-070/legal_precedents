"""
Gemini API Configuration
Gemini API 클라이언트 초기화 함수
"""

from google import genai
from google.genai import types


def initialize_client(api_key: str):
    """
    API key를 받아서 Gemini client 초기화

    Args:
        api_key: Google API key

    Returns:
        genai.Client: 초기화된 Gemini API 클라이언트
    """
    if not api_key:
        raise ValueError("API key가 제공되지 않았습니다.")

    return genai.Client(api_key=api_key)
