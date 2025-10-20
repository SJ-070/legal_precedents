"""
AI Agent Execution
AI 에이전트 실행 및 관리 모듈
"""

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from google.genai import types
from .vectorizer import search_relevant_data


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
- **중요**: 답변 시 반드시 참조한 판례의 출처를 명시하세요. 출처 표기 형식:
    - [판례번호] 제목 (판결일자)
    - 예: [조심2023관0123] 수입물품 과세가격 결정 관련 (2023.05.15)
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
- **중요**: 최종 답변 시 각 에이전트가 제시한 판례의 출처를 정리하여 명시하세요. 답변 마지막에 "참조 판례" 섹션을 추가하여 모든 출처를 나열하세요.
"""


def run_agent(client, agent_type, user_query, preprocessed_data, chunk_info, agent_index=None, conversation_history=""):
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
        # Gemini 모델 호출 - gemini-2.5-flash 모델 사용 (일반 에이전트)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
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


def run_parallel_agents(client, court_cases, tax_cases, preprocessed_data, user_query, conversation_history=""):
    """모든 에이전트를 병렬로 실행하고 완료되는 즉시 결과 yield (통합 벡터화 버전)"""
    from concurrent.futures import as_completed

    results = [None] * 6  # 순서 보장을 위한 고정 크기 리스트

    try:
        # 청크 정보 가져오기
        chunks_info = preprocessed_data["chunks_info"]

        # ThreadPoolExecutor로 병렬 처리
        with ThreadPoolExecutor(max_workers=6) as executor:
            # future -> index 매핑
            future_to_index = {}

            # 6개 에이전트 실행 (Agent 1-2: KCS, Agent 3-6: MOLEG)
            for i, chunk_info in enumerate(chunks_info, start=1):
                agent_type = chunk_info['agent_type']
                future = executor.submit(
                    run_agent, client, agent_type, user_query,
                    preprocessed_data, chunk_info, i, conversation_history
                )
                future_to_index[future] = i - 1  # 0-based index 저장

            # 완료되는 순서대로 처리하며 즉시 yield
            for future in as_completed(future_to_index.keys()):
                index = future_to_index[future]
                result = future.result()
                results[index] = result

                # 완료된 결과 즉시 반환
                yield result

        # 병렬 에이전트 완료 후 3초 대기 (TPM rate limit 여유 확보)
        logging.info("병렬 에이전트 완료, Head Agent 호출 전 3초 대기 중...")
        time.sleep(3)

    except Exception as e:
        logging.error(f"병렬 에이전트 실행 오류: {str(e)}")
        yield {
            "agent": "Error Agent",
            "response": f"에이전트 실행 중 오류가 발생했습니다: {str(e)}"
        }


def prepare_head_agent_input(agent_responses, max_tokens=200000):
    """Head Agent 입력 토큰 수 관리 - 초과 시 마지막 에이전트 응답 truncate"""
    # 간단한 토큰 추정: 한글 1자 약 2.5 토큰
    total_chars = sum(len(resp['response']) for resp in agent_responses)
    estimated_tokens = total_chars * 2.5

    logging.info(f"Head Agent 입력 예상 토큰: {int(estimated_tokens):,} (최대: {max_tokens:,})")

    if estimated_tokens > max_tokens:
        # 초과 토큰 계산
        excess_tokens = estimated_tokens - max_tokens
        reduction_chars = int(excess_tokens / 2.5)

        # Agent 6 (마지막) 응답만 truncate
        original_length = len(agent_responses[-1]['response'])
        truncated_length = max(1000, original_length - reduction_chars)  # 최소 1000자 보장

        agent_responses[-1]['response'] = agent_responses[-1]['response'][:truncated_length]

        logging.warning(f"Agent 6 응답 truncate: {original_length:,}자 -> {truncated_length:,}자")

    return agent_responses


def run_head_agent(client, agent_responses, user_query, conversation_history=""):
    """각 에이전트의 응답을 통합하여 최종 응답 생성"""
    # 토큰 관리 (입력 용량 초과 방지)
    agent_responses = prepare_head_agent_input(agent_responses, max_tokens=200000)

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
