"""
Text Vectorization and Search
텍스트 벡터화 및 검색 모듈
"""

import streamlit as st
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .text_processor import preprocess_text, extract_text_from_item


def preprocess_data(court_cases, tax_cases):
    """데이터 전처리 및 벡터화 - Character n-gram 방식으로 통합 벡터화"""
    logging.info("Character n-gram 벡터화 시작...")

    # 1. KCS와 MOLEG 데이터 통합
    all_data = []
    data_sources = []  # 각 문서의 출처 추적 ('kcs' 또는 'moleg')

    # KCS 데이터 추가
    for item in court_cases:
        all_data.append(item)
        data_sources.append('kcs')

    # MOLEG 데이터 추가
    for item in tax_cases:
        all_data.append(item)
        data_sources.append('moleg')

    logging.info(f"통합 데이터: KCS {len(court_cases)}건 + MOLEG {len(tax_cases)}건 = 총 {len(all_data)}건")

    # 2. 전체 코퍼스 생성
    corpus = []
    for i, item in enumerate(all_data):
        if data_sources[i] == 'kcs':
            text = extract_text_from_item(item, "court_case")
        else:
            text = extract_text_from_item(item, "tax_case")
        corpus.append(preprocess_text(text))

    # 3. Character n-gram TF-IDF 벡터화 (테스트에서 검증된 최고 성능 방식)
    vectorizer = TfidfVectorizer(
        analyzer='char',
        ngram_range=(2, 4),
        max_df=0.9,
        min_df=1,
        max_features=50000,  # 차원 폭발 방지
        sublinear_tf=True,
        use_idf=True,
        smooth_idf=True,
        norm='l2'
    )

    logging.info("Character n-gram 벡터화 수행 중...")
    tfidf_matrix = vectorizer.fit_transform(corpus)
    logging.info(f"벡터화 완료: {len(vectorizer.vocabulary_):,}개 character n-gram 특징")

    # 4. 에이전트별로 데이터를 6개 청크로 분할 (기존 로직 유지)
    # Agent 1-2: KCS 데이터 2분할
    kcs_size = len(court_cases)
    kcs_chunk_size = kcs_size // 2

    # Agent 3-6: MOLEG 데이터 4분할
    moleg_size = len(tax_cases)
    moleg_chunk_size = moleg_size // 4

    chunks_info = []

    # Agent 1-2 (KCS)
    for i in range(2):
        start_idx = i * kcs_chunk_size
        end_idx = (i + 1) * kcs_chunk_size if i < 1 else kcs_size
        chunks_info.append({
            'agent_type': 'court_case',
            'start_idx': start_idx,
            'end_idx': end_idx,
            'data_type': 'kcs'
        })

    # Agent 3-6 (MOLEG)
    for i in range(4):
        start_idx = kcs_size + i * moleg_chunk_size
        end_idx = kcs_size + (i + 1) * moleg_chunk_size if i < 3 else len(all_data)
        chunks_info.append({
            'agent_type': 'tax_case',
            'start_idx': start_idx,
            'end_idx': end_idx,
            'data_type': 'moleg'
        })

    # 청크 정보 로깅
    st.sidebar.info(f"데이터 분할: KCS 2개 청크 + MOLEG 4개 청크 = 총 6개 에이전트")
    logging.info(f"청크 정보: {chunks_info}")

    result = {
        "all_data": all_data,
        "corpus": corpus,
        "vectorizer": vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "data_sources": data_sources,
        "chunks_info": chunks_info,
        "kcs_size": kcs_size,
        "moleg_size": moleg_size
    }

    logging.info("Character n-gram 벡터화 완료")
    return result


def search_relevant_data(query, preprocessed_data, chunk_info, top_n=5, conversation_history=""):
    """질문과 관련성이 높은 데이터 항목을 검색 (통합 벡터화된 데이터 활용)"""
    # 쿼리 전처리
    enhanced_query = query
    if conversation_history:
        enhanced_query = f"{query} {conversation_history}"

    enhanced_query = preprocess_text(enhanced_query)

    try:
        # 통합 벡터화된 데이터 사용
        vectorizer = preprocessed_data["vectorizer"]
        tfidf_matrix = preprocessed_data["tfidf_matrix"]
        all_data = preprocessed_data["all_data"]

        # 청크 범위 추출
        start_idx = chunk_info['start_idx']
        end_idx = chunk_info['end_idx']

        # 해당 청크의 TF-IDF 행렬만 추출
        chunk_tfidf_matrix = tfidf_matrix[start_idx:end_idx]

        # 쿼리 벡터화
        query_vec = vectorizer.transform([enhanced_query])

        # 코사인 유사도 계산
        similarities = cosine_similarity(query_vec, chunk_tfidf_matrix)[0]

        # 유사도 기준으로 상위 n개 항목 선택
        top_indices = similarities.argsort()[-top_n:][::-1]

        # 유사도가 0보다 큰 항목만 선택
        relevant_data = []
        for idx in top_indices:
            if similarities[idx] > 0:
                # 전체 데이터에서의 실제 인덱스
                actual_idx = start_idx + idx
                relevant_data.append(all_data[actual_idx])

        return relevant_data
    except Exception as e:
        logging.error(f"검색 오류: {str(e)}")
        # 오류 발생 시 청크의 일부 반환
        try:
            chunk_data = all_data[start_idx:end_idx]
            return chunk_data[:min(top_n, len(chunk_data))]
        except:
            return []
