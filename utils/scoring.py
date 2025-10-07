"""
Scoring Module
판례 검색 시 유사도 점수 계산
"""

import re
from typing import Dict, Any, Optional
from .pattern_detectors import (
    detect_case_number,
    detect_precedent_number,
    detect_date,
    detect_court,
    detect_customs
)


def normalize_text(text: str) -> str:
    """
    텍스트 정규화 (띄어쓰기, 특수문자 제거)

    Args:
        text: 원본 텍스트

    Returns:
        정규화된 텍스트
    """
    if not text:
        return ""
    return re.sub(r'[^\w가-힣]', '', str(text)).lower()


def extract_numbers(text: str) -> str:
    """
    텍스트에서 숫자만 추출

    Args:
        text: 원본 텍스트

    Returns:
        숫자만 포함된 문자열
    """
    if not text:
        return ""
    return re.sub(r'\D', '', str(text))


def match_case_number_score(query: str, target: str) -> float:
    """
    사건번호 매칭 점수 계산

    Args:
        query: 사용자 입력
        target: 데이터베이스의 사건번호

    Returns:
        매칭 점수 (0-100)
    """
    query_info = detect_case_number(query)
    target_info = detect_case_number(target)

    if not query_info or not target_info:
        return 0.0

    # 완전 일치
    if query_info['full'] == target_info['full']:
        return 100.0

    # 법원명 제외 매칭 (연도 + 사건종류 + 번호)
    query_core = f"{query_info['year']}{query_info['type']}{query_info['number']}"
    target_core = f"{target_info['year']}{target_info['type']}{target_info['number']}"

    if query_core == target_core:
        # 법원명이 있으면 90점, 없으면 85점
        if query_info['court']:
            return 90.0
        return 85.0

    # 부분 일치
    if query_core in target_core or target_core in query_core:
        return 70.0

    # 번호만 일치
    if query_info['number'] == target_info['number']:
        return 50.0

    return 0.0


def match_precedent_number_score(query: str, target: str) -> float:
    """
    판례번호 매칭 점수 계산

    Args:
        query: 사용자 입력
        target: 데이터베이스의 판례번호

    Returns:
        매칭 점수 (0-100)
    """
    query_info = detect_precedent_number(query)
    target_info = detect_precedent_number(target)

    if not query_info or not target_info:
        return 0.0

    # 완전 일치
    if normalize_text(query) == normalize_text(target):
        return 100.0

    # 사건번호만 일치 (예: 2023도1907)
    if query_info['case_id'] == target_info['case_id']:
        return 90.0

    # 법원명 + 사건번호 일치
    if query_info.get('court') and target_info.get('court'):
        if query_info['court'] == target_info['court'] and query_info['case_id'] == target_info['case_id']:
            return 85.0

    # 연도 + 사건종류 일치
    query_year = query_info['case_id'][:4]
    target_year = target_info['case_id'][:4]
    query_type = re.search(r'[가-힣]+', query_info['case_id'])
    target_type = re.search(r'[가-힣]+', target_info['case_id'])

    if query_year == target_year and query_type and target_type:
        if query_type.group(0) == target_type.group(0):
            return 60.0

    return 0.0


def match_date_score(query_date: str, target_date: str) -> float:
    """
    날짜 매칭 점수 계산

    Args:
        query_date: 사용자 입력 날짜 (정규화된 형식)
        target_date: 데이터베이스의 날짜

    Returns:
        매칭 점수 (0-100)
    """
    if not query_date or not target_date:
        return 0.0

    # 정규화
    query_normalized = normalize_text(query_date)
    target_normalized = normalize_text(target_date)

    # 완전 일치
    if query_normalized == target_normalized:
        return 100.0

    # 날짜 파싱 시도
    try:
        # YYYY-MM-DD 형식으로 분리
        query_parts = query_date.split('-')
        target_parts = target_date.split('-') if '-' in target_date else target_date.split('.')

        if len(query_parts) >= 1 and len(target_parts) >= 1:
            # 연도만 일치
            if query_parts[0] == target_parts[0]:
                if len(query_parts) >= 2 and len(target_parts) >= 2:
                    # 연월 일치
                    if query_parts[1].zfill(2) == target_parts[1].zfill(2):
                        return 70.0
                return 40.0
    except:
        pass

    return 0.0


def match_court_score(query: str, target: str) -> float:
    """
    법원명 매칭 점수 계산

    Args:
        query: 사용자 입력
        target: 데이터베이스의 법원명

    Returns:
        매칭 점수 (0-100)
    """
    if not query or not target:
        return 0.0

    query_info = detect_court(query)
    target_info = detect_court(target)

    if not query_info or not target_info:
        # 직접 텍스트 비교
        if normalize_text(query) == normalize_text(target):
            return 100.0
        if normalize_text(query) in normalize_text(target):
            return 70.0
        return 0.0

    # 정식명칭 일치
    if query_info['normalized_name'] == target_info['normalized_name']:
        # 둘 다 정식명칭인 경우
        if not query_info['is_alias'] and not target_info['is_alias']:
            return 100.0
        # 하나라도 약칭인 경우
        return 95.0

    # 부분 일치
    if query_info['normalized_name'] in target_info['normalized_name'] or \
       target_info['normalized_name'] in query_info['normalized_name']:
        return 70.0

    return 0.0


def match_customs_score(query: str, target: str) -> float:
    """
    세관명 매칭 점수 계산

    Args:
        query: 사용자 입력
        target: 데이터베이스의 세관명

    Returns:
        매칭 점수 (0-100)
    """
    if not query or not target:
        return 0.0

    query_info = detect_customs(query)
    target_info = detect_customs(target)

    if not query_info or not target_info:
        # 직접 텍스트 비교
        if normalize_text(query) == normalize_text(target):
            return 100.0
        if normalize_text(query) in normalize_text(target):
            return 70.0
        return 0.0

    # 정식명칭 일치
    if query_info['normalized_name'] == target_info['normalized_name']:
        # 둘 다 정식명칭인 경우
        if not query_info['is_alias'] and not target_info['is_alias']:
            return 100.0
        # 하나라도 약칭인 경우
        return 95.0

    # 부분 일치
    if query_info['normalized_name'] in target_info['normalized_name'] or \
       target_info['normalized_name'] in query_info['normalized_name']:
        return 70.0

    return 0.0


def calculate_precedent_score(query: str, precedent_data: Dict[str, Any], source: str) -> float:
    """
    판례 전체 유사도 점수 계산 (가중치 기반)

    Args:
        query: 사용자 검색어
        precedent_data: 판례 데이터 (KCS 또는 MOLEG)
        source: 'kcs' 또는 'moleg'

    Returns:
        최종 유사도 점수 (0-100)
    """
    # 필드별 점수 및 가중치 저장
    field_scores = {}

    # 사건번호/판례번호 매칭 (가중치 60%)
    if source == 'kcs' and '사건번호' in precedent_data:
        score = match_case_number_score(query, precedent_data['사건번호'])
        if score > 0:
            field_scores['case_number'] = {'score': score, 'weight': 0.6}
    elif source == 'moleg' and '판례번호' in precedent_data:
        score = match_precedent_number_score(query, precedent_data['판례번호'])
        if score > 0:
            field_scores['precedent_number'] = {'score': score, 'weight': 0.6}

    # 날짜 매칭 (가중치 20%)
    detected_dates = detect_date(query)
    if detected_dates:
        date_field = '선고일자\n(종결일자)' if source == 'kcs' else '선고일자'
        if date_field in precedent_data:
            max_date_score = 0
            for detected_date in detected_dates:
                score = match_date_score(detected_date, precedent_data[date_field])
                max_date_score = max(max_date_score, score)
            if max_date_score > 0:
                field_scores['date'] = {'score': max_date_score, 'weight': 0.2}

    # 법원명 매칭 (MOLEG만, 가중치 20%)
    if source == 'moleg' and '법원명' in precedent_data:
        court_info = detect_court(query)
        if court_info:
            score = match_court_score(query, precedent_data['법원명'])
            if score > 0:
                field_scores['court'] = {'score': score, 'weight': 0.2}

    # 처분청 매칭 (KCS만, 가중치 20%)
    if source == 'kcs' and '처분청' in precedent_data:
        customs_info = detect_customs(query)
        if customs_info:
            score = match_customs_score(query, precedent_data['처분청'])
            if score > 0:
                field_scores['customs'] = {'score': score, 'weight': 0.2}

    # 점수 계산 로직
    if not field_scores:
        return 0.0

    # 가중치 기반 점수 계산
    total_weighted_score = 0.0
    total_weight = 0.0
    matched_fields_count = len(field_scores)

    for field_name, field_data in field_scores.items():
        total_weighted_score += field_data['score'] * field_data['weight']
        total_weight += field_data['weight']

    # 가중 평균 계산 (사용된 가중치의 비율로 정규화)
    if total_weight > 0:
        base_score = total_weighted_score / total_weight
    else:
        base_score = 0.0

    # 복수 필드 매칭 보너스
    multi_field_bonus = 0.0
    if matched_fields_count == 2:
        multi_field_bonus = 5.0
    elif matched_fields_count >= 3:
        multi_field_bonus = 10.0

    # 최종 점수 = 기본 점수 + 매칭 보너스
    final_score = base_score + multi_field_bonus

    # 최대 100점으로 제한
    return min(final_score, 100.0)


def get_matched_fields(query: str, precedent_data: Dict[str, Any], source: str) -> Dict[str, float]:
    """
    검색어와 매칭된 필드 정보를 반환

    Args:
        query: 사용자 검색어
        precedent_data: 판례 데이터 (KCS 또는 MOLEG)
        source: 'kcs' 또는 'moleg'

    Returns:
        매칭된 필드와 점수 딕셔너리
        {
            'case_number': 100.0,
            'date': 90.0,
            'court': 95.0
        }
    """
    matched_fields = {}

    # 사건번호/판례번호 매칭
    if source == 'kcs' and '사건번호' in precedent_data:
        score = match_case_number_score(query, precedent_data['사건번호'])
        if score > 0:
            matched_fields['사건번호'] = score
    elif source == 'moleg' and '판례번호' in precedent_data:
        score = match_precedent_number_score(query, precedent_data['판례번호'])
        if score > 0:
            matched_fields['판례번호'] = score

    # 날짜 매칭
    detected_dates = detect_date(query)
    if detected_dates:
        date_field = '선고일자\n(종결일자)' if source == 'kcs' else '선고일자'
        if date_field in precedent_data:
            max_date_score = 0
            for detected_date in detected_dates:
                score = match_date_score(detected_date, precedent_data[date_field])
                max_date_score = max(max_date_score, score)
            if max_date_score > 0:
                matched_fields['선고일자'] = max_date_score

    # 법원명 매칭
    if source == 'moleg' and '법원명' in precedent_data:
        court_info = detect_court(query)
        if court_info:
            score = match_court_score(query, precedent_data['법원명'])
            if score > 0:
                matched_fields['법원명'] = score

    # 처분청 매칭
    if source == 'kcs' and '처분청' in precedent_data:
        customs_info = detect_customs(query)
        if customs_info:
            score = match_customs_score(query, precedent_data['처분청'])
            if score > 0:
                matched_fields['처분청'] = score

    return matched_fields
