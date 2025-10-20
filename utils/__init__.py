"""
Legal Precedents Chatbot Utilities
관세법 판례 챗봇 유틸리티 모듈
"""

# 설정
from .config import initialize_client

# 대화 관리
from .conversation import get_conversation_history

# 데이터 로더
from .data_loader import (
    check_data_files,
    extract_zip_file,
    load_data,
    save_vectorization_cache,
    load_vectorization_cache
)

# 텍스트 처리
from .text_processor import preprocess_text, extract_text_from_item

# 벡터화 및 검색
from .vectorizer import preprocess_data, search_relevant_data

# 에이전트
from .agent import (
    get_agent_prompt,
    run_agent,
    run_parallel_agents,
    prepare_head_agent_input,
    run_head_agent
)

# 판례 검색
from .precedent_search import (
    search_precedent,
    format_precedent_title,
    format_precedent_summary
)

__all__ = [
    # 설정
    'initialize_client',

    # 대화 관리
    'get_conversation_history',

    # 데이터 로더
    'check_data_files', 'extract_zip_file', 'load_data',
    'save_vectorization_cache', 'load_vectorization_cache',

    # 텍스트 처리
    'preprocess_text', 'extract_text_from_item',

    # 벡터화 및 검색
    'preprocess_data', 'search_relevant_data',

    # 에이전트
    'get_agent_prompt', 'run_agent', 'run_parallel_agents',
    'prepare_head_agent_input', 'run_head_agent',

    # 판례 검색
    'search_precedent', 'format_precedent_title', 'format_precedent_summary'
]
