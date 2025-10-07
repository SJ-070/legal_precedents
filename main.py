import streamlit as st
import os
import time
import logging
from dotenv import load_dotenv
from utils import (
    
    check_data_files,
    load_data,
    run_parallel_agents,
    run_head_agent,
    get_conversation_history
)

# # --- 환경 변수 및 Gemini API 설정 ---
# load_dotenv()
# GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
# genai.configure(api_key=GOOGLE_API_KEY)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 페이지 설정
st.set_page_config(
    page_title="관세법 판례 기반 챗봇",
    page_icon="⚖️",
    layout="wide",
)

# 애플리케이션 제목
st.title("⚖️ 관세법 판례 기반 챗봇")
st.markdown("관세법 판례 정보를 활용한 AI 기반 법률 챗봇입니다.")


# 대화 관련 설정
if "messages" not in st.session_state:
    st.session_state.messages = []

if "processing" not in st.session_state:
    st.session_state.processing = False

# 대화 맥락 관리 설정
if "context_enabled" not in st.session_state:
    st.session_state.context_enabled = True

# 데이터 저장을 위한 세션 상태 설정
if "loaded_data" not in st.session_state:
    st.session_state.loaded_data = {
        "court_cases": [],
        "tax_cases": [],
        "preprocessed_data": {}
    }

with st.sidebar:
    st.header("설정")
    
    
    # 대화 관리 옵션들
    st.header("대화 관리")
    
    # 대화 맥락 활용 옵션
    context_enabled = st.checkbox("이전 대화 맥락 활용", value=st.session_state.context_enabled)
    if context_enabled != st.session_state.context_enabled:
        st.session_state.context_enabled = context_enabled
        if context_enabled:
            st.success("이전 대화 맥락을 활용합니다.")
        else:
            st.info("각 질문을 독립적으로 처리합니다.")
    
    # 최근 대화 유지 수 선택
    if st.session_state.context_enabled:
        max_history = st.slider("최근 대화 유지 수", min_value=2, max_value=10, value=5)
        st.session_state.max_history = max_history
    
    # 새로운 대화 시작 버튼
    if st.button("새로운 대화 시작하기"):
        # 메시지 기록만 초기화 (데이터는 유지)
        st.session_state.messages = []
        st.session_state.processing = False
        st.success("새로운 대화가 시작되었습니다.")

# 실행 시 데이터 파일 존재 여부 확인
has_data_files = check_data_files()
if not has_data_files:
    st.warning("일부 데이터 파일이 없습니다. 예시 데이터를 사용하거나 필요한 파일을 추가해주세요.")
else:
    # 데이터가 아직 로드되지 않았다면 로드
    if not st.session_state.loaded_data["court_cases"]:
        with st.spinner("데이터를 로드하고 전처리 중입니다..."):
            court_cases, tax_cases, preprocessed_data = load_data()
            st.session_state.loaded_data = {
                "court_cases": court_cases,
                "tax_cases": tax_cases,
                "preprocessed_data": preprocessed_data
            }
            st.success("데이터 로드 및 전처리가 완료되었습니다.")

# 저장된 메시지 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 입력 처리
if prompt := st.chat_input("질문을 입력하세요..."):
    
    # 사용자 메시지 표시
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # 처리 시작
    st.session_state.processing = True
    
    # 응답 생성
    with st.chat_message("assistant"):
        try:
            # 저장된 데이터 사용
            court_cases = st.session_state.loaded_data["court_cases"]
            tax_cases = st.session_state.loaded_data["tax_cases"]
            preprocessed_data = st.session_state.loaded_data["preprocessed_data"]

            # 대화 맥락 가져오기
            conversation_history = ""
            if st.session_state.context_enabled:
                conversation_history = get_conversation_history(
                    max_messages=st.session_state.get('max_history', 5)
                )

            # === [섹션 1] 실시간 진행 상황 표시 ===
            progress_display = st.empty()

            # === [섹션 2] 에이전트 답변 동적 표시 (st.status) ===
            agent_status = st.status("🤖 에이전트 답변 생성 중...", expanded=True, state='running')

            # 에이전트 컨테이너 6개 미리 생성
            agent_containers = []
            with agent_status:
                for i in range(6):
                    agent_containers.append(st.empty())

            # === [섹션 3] 최종 답변 (예약) ===
            final_answer_section = st.empty()

            # === 에이전트 병렬 실행 및 실시간 UI 업데이트 ===
            progress_display.markdown("⏳ 에이전트 실행 중...")

            # 제너레이터로 실시간 처리
            agent_responses = []
            completed_count = 0

            for result in run_parallel_agents(
                court_cases, tax_cases, preprocessed_data, prompt, conversation_history
            ):
                # 에이전트 인덱스 추출 (예: "Agent 3" -> 2)
                agent_num = int(result['agent'].split()[-1]) - 1

                # 즉시 UI 업데이트
                with agent_containers[agent_num].container():
                    st.subheader(f"📋 {result['agent']}")
                    st.markdown(result['response'])
                    if agent_num < 5:
                        st.divider()

                completed_count += 1
                progress_display.markdown(f"✓ {result['agent']} 완료 ({completed_count}/6)")

                agent_responses.append(result)

            # 순서대로 정렬 (완료 순서가 다를 수 있으므로)
            agent_responses.sort(key=lambda x: int(x['agent'].split()[-1]))

            # 모든 에이전트 완료
            progress_display.markdown("✓ 모든 에이전트 완료 | ⏳ 최종 답변 통합 중...")

            # === Head Agent로 최종 응답 생성 ===
            head_response = run_head_agent(
                agent_responses, prompt, conversation_history
            )

            # 응답 텍스트 추출
            if isinstance(head_response, dict):
                final_response = head_response.get("response", "응답을 생성할 수 없습니다.")
            else:
                final_response = head_response

            # === [섹션 2] 자동으로 닫기 ===
            agent_status.update(
                label="🤖 각 에이전트 답변 보기",
                state="complete",
                expanded=False
            )

            # === [섹션 1] 완료 상태 ===
            progress_display.markdown("✅ 답변 생성 완료!")
            time.sleep(0.3)
            progress_display.empty()

            # === [섹션 3] 최종 답변 표시 ===
            with final_answer_section.container():
                st.markdown("### 📌 최종 답변")
                st.markdown(final_response)

            # 응답 저장
            st.session_state.messages.append({"role": "assistant", "content": final_response})

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")
            logging.error(f"전체 처리 오류: {str(e)}")
            # 오류 메시지도 저장
            error_message = f"오류가 발생했습니다: {str(e)}"
            st.session_state.messages.append({"role": "assistant", "content": error_message})
    
    # 처리 완료
    st.session_state.processing = False

# 사이드바에 사용 예시 및 정보 추가
with st.sidebar:
    st.subheader("프로젝트 정보")
    st.markdown("""
    이 챗봇은 관세법 판례를 기반으로 답변을 생성합니다.

    **데이터 소스**
    - KCS 판례: 423건
    - MOLEG 판례: 486건
    - 총 909건의 판례 데이터

    **시스템 구조**
    - 6개의 AI 에이전트 병렬 실행
    - Google Gemini 2.5 Flash 모델 사용
    - Character n-gram TF-IDF 검색
    - Multi-Agent 통합 답변 생성

    **주요 장점**
    - 완전 무료 (Gemini API 무료 티어)
    - 일반 노트북/무료 Streamlit Cloud 구동
    - 빠른 응답 (검색 0.05초, 답변 5-10초)
    """)