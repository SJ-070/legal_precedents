"""
Conversation History Management
대화 기록 관리 모듈
"""

import streamlit as st


def get_conversation_history(max_messages=10):
    """최근 대화 기록을 문자열로 반환"""
    if "messages" not in st.session_state or len(st.session_state.messages) <= 1:
        return ""

    # 가장 최근 메시지는 현재 처리중인 사용자 질문이므로 제외
    messages = st.session_state.messages[:-1]

    # 최대 메시지 수를 제한하여 컨텍스트 길이 관리
    if len(messages) > max_messages:
        messages = messages[-max_messages:]

    conversation = ""
    for msg in messages:
        role = "사용자" if msg["role"] == "user" else "챗봇"
        conversation += f"{role}: {msg['content']}\n\n"

    return conversation
