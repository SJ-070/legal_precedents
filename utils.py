import streamlit as st
import json
import os
from concurrent.futures import ThreadPoolExecutor
import logging
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import zipfile
import tempfile
from dotenv import load_dotenv
import pickle
import hashlib

# --- 환경 변수 및 Gemini API 설정 ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
from google import genai
from google.genai import types
client = genai.Client(api_key=GOOGLE_API_KEY)

# 대화 기록 관리 함수
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

# 데이터 파일 존재 여부 확인 함수
def check_data_files():
    """필요한 데이터 파일 존재 여부 확인"""
    court_file = "data_kcs.json"
    tax_file = "data_moleg.json"
    
    files_exist = True
    if not os.path.exists(court_file):
        st.sidebar.error(f"파일을 찾을 수 없습니다: {court_file}")
        files_exist = False
    if not os.path.exists(tax_file):
        st.sidebar.error(f"파일을 찾을 수 없습니다: {tax_file}")
        files_exist = False
        
    return files_exist

# ZIP 파일 압축 해제 함수
def extract_zip_file(zip_path):
    """ZIP 파일을 임시 디렉토리에 압축 해제하고 JSON 파일 내용 반환"""
    try:
        # 임시 디렉토리 생성
        with tempfile.TemporaryDirectory() as temp_dir:
            # ZIP 파일 압축 해제
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # JSON 파일 찾기 (첫 번째 JSON 파일 사용)
            json_files = [f for f in os.listdir(temp_dir) if f.endswith('.json')]
            if not json_files:
                raise FileNotFoundError("ZIP 파일 내에 JSON 파일이 없습니다.")
            
            # JSON 파일 로드
            json_path = os.path.join(temp_dir, json_files[0])
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
    except Exception as e:
        st.sidebar.error(f"ZIP 파일 처리 오류: {str(e)}")
        logging.error(f"ZIP 파일 처리 오류: {str(e)}")
        return []

# 텍스트 전처리 함수
def preprocess_text(text):
    """텍스트 정규화 및 전처리"""
    if not text or not isinstance(text, str):
        return ""
    # 공백 정규화 및 특수문자 처리
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
    text = text.strip()  # 앞뒤 공백 제거
    return text

# 데이터에서 텍스트 추출 함수
def extract_text_from_item(item, data_type):
    """데이터 아이템에서 검색에 사용할 텍스트 추출"""
    if data_type == "court_case":
        # 판례 데이터에서 텍스트 추출
        text_parts = []
        for key in ['사건번호', '선고일자\n(종결일자)', '판결주문', '청구취지', '판결이유']:
            if key in item and item[key]:
                sub_text = f'{key}: {item[key]} \n\n'
                text_parts.append(sub_text)
        return ' '.join(text_parts)
    else:  # 국가법령정보센터_관세판례 (MOLEG)
        # clean_moleg.py로 구조화된 필드들을 활용한 텍스트 추출
        text_parts = []

        # 가중치 설정: 판결요지 50%, 나머지 8개 필드가 50%를 균등분배
        # 나머지 필드 가중치 = 0.5 / 8 = 0.0625 each
        field_weights = {
            '제목': 0.0625,
            '판례번호': 0.0625,
            '내용': 0.0625,
            '선고일자': 0.0625,
            '법원명': 0.0625,
            '사건유형': 0.0625,
            '판결요지': 0.5,        # 가장 높은 가중치
            '참조조문': 0.0625,
            '판결결과': 0.0625
        }

        for field, weight in field_weights.items():
            if field in item and item[field]:
                field_text = f'{field}: {item[field]} \n\n'
                # 가중치를 적용하여 중요한 필드를 더 많이 반복
                repeat_count = max(1, int(weight * 10))  # 가중치 * 10으로 반복 횟수 결정
                for _ in range(repeat_count):
                    text_parts.append(field_text)

        return ' '.join(text_parts)
    

# 캐시 키 생성 함수
def get_cache_key():
    """데이터 파일의 수정 시간을 기반으로 캐시 키 생성"""
    try:
        kcs_mtime = os.path.getmtime("data_kcs.json")
        moleg_mtime = os.path.getmtime("data_moleg.json")
        cache_string = f"{kcs_mtime}_{moleg_mtime}"
        return hashlib.md5(cache_string.encode()).hexdigest()
    except:
        return "default"

# 벡터화 결과 저장 함수
def save_vectorization_cache(preprocessed_data, cache_key):
    """벡터화 결과를 pickle 파일로 저장"""
    cache_file = f"vectorization_cache_{cache_key}.pkl"
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(preprocessed_data, f)
        logging.info(f"벡터화 캐시 저장 완료: {cache_file}")
        return True
    except Exception as e:
        logging.error(f"벡터화 캐시 저장 실패: {str(e)}")
        return False

# 벡터화 결과 로드 함수
def load_vectorization_cache(cache_key):
    """저장된 벡터화 결과를 pickle 파일에서 로드"""
    cache_file = f"vectorization_cache_{cache_key}.pkl"
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                preprocessed_data = pickle.load(f)
            logging.info(f"벡터화 캐시 로드 완료: {cache_file}")
            return preprocessed_data
        return None
    except Exception as e:
        logging.error(f"벡터화 캐시 로드 실패: {str(e)}")
        return None

# 데이터 로드 함수 - 초기화 시 1번만 호출
@st.cache_data
def load_data():
    """판례 데이터 로드"""
    try:
        # 판례 데이터 로드1
        with open("data_kcs.json", "r", encoding="utf-8") as f:
            court_cases = json.load(f)
        st.sidebar.success(f"KCS 판례 데이터 로드 완료: {len(court_cases)}건")

        # 판례 데이터 로드2
        with open("data_moleg.json", "r", encoding="utf-8") as f:
            tax_cases = json.load(f)
        st.sidebar.success(f"MOLEG 판례 데이터 로드 완료: {len(tax_cases)}건")

        # 캐시 키 생성
        cache_key = get_cache_key()

        # 캐시된 벡터화 결과 확인
        preprocessed_data = load_vectorization_cache(cache_key)

        if preprocessed_data is not None:
            st.sidebar.info("저장된 벡터화 인덱스를 로드했습니다.")
        else:
            # 캐시가 없으면 데이터 전처리 및 벡터화 수행
            st.sidebar.info("벡터화 인덱스를 생성 중입니다...")
            preprocessed_data = preprocess_data(court_cases, tax_cases)
            # 벡터화 결과 저장
            save_vectorization_cache(preprocessed_data, cache_key)
            st.sidebar.success("벡터화 인덱스 생성 및 저장 완료!")

        return court_cases, tax_cases, preprocessed_data

    except FileNotFoundError as e:
        st.sidebar.error(f"파일을 찾을 수 없습니다: {e}")
        st.error("필수 데이터 파일을 찾을 수 없습니다. 애플리케이션 디렉토리에 필요한 파일이 있는지 확인하세요.")
        return [], [], {}
    except json.JSONDecodeError as e:
        st.sidebar.error(f"JSON 파일 파싱 오류: {e}")
        st.error("JSON 파일 형식이 올바르지 않습니다. 파일 형식을 확인하세요.")
        return [], [], {}

# 새로운 함수: 데이터 전처리 및 벡터화 (최초 1회만 실행)
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


# 관련성 높은 데이터 검색 함수 - Character n-gram 방식
def search_relevant_data(query, preprocessed_data, chunk_info, top_n=10, conversation_history=""):
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

# 에이전트 프롬프트 정의
def get_agent_prompt(agent_type):
    """에이전트 유형에 따른 프롬프트 생성"""
    base_prompt = """
# Role
- 당신은 관세법 분야 전문성을 갖춘 법학 교수입니다.
- 당신은 판결문의 논리와 판사의 의도를 이해하고, 복잡한 법적 문제를 분석하는 능력이 탁월합니다.
- 사용자의 질문에 대해 주어진 데이터를 활용하여 상세하게 답변합니다.
- 주요 답변 내용:
    1. 판결문의 주요 내용 요약
    2. 주요 법적 쟁점 도출
    3. 법원의 판단 요지 및 그 근거 요약
    4. 법원이 인용한 주요 법률 조항 및 판례 설명
- 모든 답변은 두괄식으로 작성합니다.
"""
    if agent_type == "court_case":
        return base_prompt + "\n# 판례 데이터를 기반으로 응답하세요. 모르면 모른다고 하세요."
    elif agent_type == "tax_case":
        return base_prompt + "\n# 판례 데이터를 기반으로 응답하세요. 모르면 모른다고 하세요."
    else:  # head agent
        return """
# Role
- 당신은 관세법 분야 전문성을 갖춘 법학 교수이자 여러 자료를 통합하여 종합적인 답변을 제공하는 전문가입니다.
- 여러 에이전트로부터 받은 답변을 분석하고 통합하여 사용자의 질문에 가장 적합한 최종 답변을 제공합니다.
- 주요 역할:
    1. 서로 다른 정보 소스에서 나온 답변을 비교 분석
    2. 가장 관련성 높은 정보 선별
    3. 일관된 논리구조로 통합된 답변 생성
    4. 중복 정보 제거 및 핵심 정보 강조
    5. 이전 대화 맥락을 고려하여 답변 작성
- 모든 답변은 두괄식으로 작성합니다.
- 이전 대화에서 언급된 내용이 있다면 그것을 기억하고 관련 내용을 참조하여 응답합니다.
"""

# 에이전트 실행 함수 - Character n-gram 방식
def run_agent(agent_type, user_query, preprocessed_data, chunk_info, agent_index=None, conversation_history=""):
    """특정 유형의 에이전트 실행 (통합 벡터화 데이터 사용)"""
    # 프롬프트 생성
    prompt = get_agent_prompt(agent_type)

    # 질문과 관련성이 높은 데이터 검색
    relevant_data = search_relevant_data(
        user_query, preprocessed_data, chunk_info,
        conversation_history=conversation_history
    )

    # 관련 데이터가 없는 경우 처리
    if not relevant_data:
        agent_label = f"Agent {agent_index}" if agent_index else "Head Agent"
        return {
            "agent": agent_label,
            "response": "관련된 데이터를 찾을 수 없습니다."
        }

    # 데이터 문자열로 변환
    data_str = json.dumps(relevant_data, ensure_ascii=False, indent=2)

    # 대화 기록 추가
    context_str = ""
    if conversation_history:
        context_str = f"\n\n# 이전 대화 기록\n{conversation_history}"

    # 전체 프롬프트 구성
    full_prompt = f"{prompt}{context_str}\n\n# 데이터\n{data_str}\n\n# 질문\n{user_query}"
    logging.info(f"Agent {agent_index if agent_index else 'Head'} 실행 시작 (관련 데이터: {len(relevant_data)}건)")

    try:
        # Gemini 모델 호출 - gemini-2.0-flash 모델 사용
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_k=5,
                top_p=0.8
            )
        )

        agent_label = f"Agent {agent_index}" if agent_index else "Head Agent"
        logging.info(f"{agent_label} 응답 생성 완료")
        return {
            "agent": agent_label,
            "response": response.text
        }
    except Exception as e:
        error_msg = f"오류 발생: {str(e)}"
        logging.error(f"Agent {agent_index if agent_index else 'Head'} 오류: {error_msg}")
        return {
            "agent": f"Agent {agent_index}" if agent_index else "Head Agent",
            "response": error_msg
        }

# 병렬 에이전트 실행 - Character n-gram 방식
def run_parallel_agents(court_cases, tax_cases, preprocessed_data, user_query, conversation_history=""):
    """모든 에이전트를 병렬로 실행하고 결과 반환 (통합 벡터화 버전)"""
    results = []

    try:
        # 청크 정보 가져오기
        chunks_info = preprocessed_data["chunks_info"]

        # ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = []

            # 6개 에이전트 실행 (Agent 1-2: KCS, Agent 3-6: MOLEG)
            for i, chunk_info in enumerate(chunks_info, start=1):
                agent_type = chunk_info['agent_type']
                futures.append(
                    executor.submit(
                        run_agent, agent_type, user_query,
                        preprocessed_data, chunk_info, i, conversation_history
                    )
                )

            # 결과 수집
            for future in futures:
                results.append(future.result())

    except Exception as e:
        logging.error(f"병렬 에이전트 실행 오류: {str(e)}")
        results.append({
            "agent": "Error Agent",
            "response": f"에이전트 실행 중 오류가 발생했습니다: {str(e)}"
        })

    return results

# Head Agent를 실행하여 최종 응답 생성
def run_head_agent(agent_responses, user_query, conversation_history=""):
    """각 에이전트의 응답을 통합하여 최종 응답 생성"""
    # 응답 데이터 준비
    responses_str = ""
    for resp in agent_responses:
        responses_str += f"\n## {resp['agent']} 응답:\n{resp['response']}\n\n"
    
    # Head Agent 프롬프트 생성
    prompt = get_agent_prompt("head")
    
    # 대화 맥락 추가
    context_str = ""
    if conversation_history:
        context_str = f"\n\n# 이전 대화 기록\n{conversation_history}"
    
    full_prompt = f"{prompt}{context_str}\n\n# 에이전트 응답\n{responses_str}\n\n# 질문\n{user_query}\n\n# 지시사항\n위 에이전트들의 응답을 통합하여 사용자의 질문에 가장 적합한 최종 답변을 작성하세요. 이전 대화 맥락을 고려하여 일관성 있게 응답하세요."
    
    try:
        # Gemini 모델 호출
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                top_k=5,
                top_p=0.8
            )
        )
        
        
        logging.info("Head Agent 응답 생성 완료")
        return {
            "agent": "Head Agent",
            "response": response.text
        }

    except Exception as e:
        error_msg = f"Head Agent 오류 발생: {str(e)}"
        logging.error(error_msg)
        return error_msg
