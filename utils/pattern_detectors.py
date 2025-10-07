"""
Pattern Detection Module
사용자 입력에서 사건번호, 판례번호, 날짜, 법원명, 처분청 등을 탐지
"""

import re
from typing import Optional, Dict, List
from datetime import datetime


# ==================== 정규식 패턴 정의 ====================

# 사건번호 패턴 (예: 대전지법2023구합208027, 2023구합208027)
CASE_NUMBER_PATTERN = r'([가-힣]+(?:지법|고법|대법원))?(\d{4})([가-힣]+)(\d+)'

# 판례번호 패턴 (예: [대법원 2025. 2. 13. 선고 2023도1907 판결])
PRECEDENT_NUMBER_FULL_PATTERN = r'\[([가-힣]+)\s+(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*선고\s+(\d{4}[가-힣]+\d+)\s*판결\]'

# 간소화된 사건번호 패턴 (예: 2023도1907)
SIMPLE_CASE_PATTERN = r'(\d{4})([가-힣]+)(\d+)'

# 날짜 패턴들
DATE_PATTERNS = [
    (r'(\d{4})-(\d{1,2})-(\d{1,2})', 'hyphen'),           # 2024-12-19
    (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', 'dot'),            # 2024.12.19
    (r'(\d{4})\s+(\d{1,2})\.\s*(\d{1,2})', 'space_dot'),  # 2024 12. 19
    (r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', 'korean'),  # 2024년 12월 19일
    (r'(\d{8})', 'compact'),                              # 20241219
]


# ==================== 법원명 사전 ====================

COURT_ALIASES = {
    "대법원": ["대법원"],
    "서울고법": ["서울고등법원", "서울고법"],
    "서울고등법원": ["서울고등법원", "서울고법"],
    "부산고법": ["부산고등법원", "부산고법"],
    "부산고등법원": ["부산고등법원", "부산고법"],
    "대구고법": ["대구고등법원", "대구고법"],
    "대구고등법원": ["대구고등법원", "대구고법"],
    "광주고법": ["광주고등법원", "광주고법"],
    "광주고등법원": ["광주고등법원", "광주고법"],
    "대전고법": ["대전고등법원", "대전고법"],
    "대전고등법원": ["대전고등법원", "대전고법"],
    "서울중앙지법": ["서울중앙지방법원", "서울중앙지법"],
    "서울지법": ["서울중앙지방법원", "서울지법"],
    "인천지법": ["인천지방법원", "인천지법"],
    "인천지방법원": ["인천지방법원", "인천지법"],
    "수원지법": ["수원지방법원", "수원지법"],
    "수원지방법원": ["수원지방법원", "수원지법"],
    "부산지법": ["부산지방법원", "부산지법"],
    "부산지방법원": ["부산지방법원", "부산지법"],
    "대구지법": ["대구지방법원", "대구지법"],
    "대구지방법원": ["대구지방법원", "대구지법"],
    "대전지법": ["대전지방법원", "대전지법"],
    "대전지방법원": ["대전지방법원", "대전지법"],
    "광주지법": ["광주지방법원", "광주지법"],
    "광주지방법원": ["광주지방법원", "광주지법"],
    "울산지법": ["울산지방법원", "울산지법"],
    "울산지방법원": ["울산지방법원", "울산지법"],
    "창원지법": ["창원지방법원", "창원지법"],
    "창원지방법원": ["창원지방법원", "창원지법"],
    "의정부지법": ["의정부지방법원", "의정부지법"],
    "의정부지방법원": ["의정부지방법원", "의정부지법"],
}


# ==================== 세관명 사전 ====================

CUSTOMS_ALIASES = {
    "인천공항세관": ["인천공항세관", "인천공항"],
    "인천세관": ["인천세관"],
    "서울세관": ["서울세관", "서울본부세관"],
    "부산세관": ["부산세관", "부산본부세관"],
    "대전세관": ["대전세관"],
    "대구세관": ["대구세관"],
    "광주세관": ["광주세관"],
    "평택세관": ["평택세관"],
    "천안세관": ["천안세관"],
}


# ==================== 탐지 함수들 ====================

def detect_case_number(query: str) -> Optional[Dict[str, str]]:
    """
    사건번호 탐지

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 사건번호 정보 또는 None
        {
            'court': '대전지법',
            'year': '2023',
            'type': '구합',
            'number': '208027',
            'full': '대전지법2023구합208027'
        }
    """
    match = re.search(CASE_NUMBER_PATTERN, query)
    if match:
        court, year, case_type, number = match.groups()
        return {
            'court': court or '',
            'year': year,
            'type': case_type,
            'number': number,
            'full': f"{court or ''}{year}{case_type}{number}"
        }
    return None


def detect_precedent_number(query: str) -> Optional[Dict[str, str]]:
    """
    판례번호 탐지

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 판례번호 정보 또는 None
        {
            'court': '대법원',
            'date': '2025-02-13',
            'case_id': '2023도1907',
            'full': '[대법원 2025. 2. 13. 선고 2023도1907 판결]'
        }
    """
    # 완전한 판례번호 패턴 먼저 시도
    match = re.search(PRECEDENT_NUMBER_FULL_PATTERN, query)
    if match:
        court, year, month, day, case_id = match.groups()
        return {
            'court': court,
            'date': f"{year}-{month.zfill(2)}-{day.zfill(2)}",
            'case_id': case_id,
            'full': match.group(0)
        }

    # 간소화된 사건번호 패턴 시도 (예: 2023도1907)
    match = re.search(SIMPLE_CASE_PATTERN, query)
    if match:
        year, case_type, number = match.groups()
        case_id = f"{year}{case_type}{number}"
        return {
            'court': '',
            'date': '',
            'case_id': case_id,
            'full': case_id
        }

    return None


def detect_date(query: str) -> List[str]:
    """
    날짜 탐지 및 정규화

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 날짜 리스트 (YYYY-MM-DD 형식)
    """
    dates = []

    for pattern, pattern_type in DATE_PATTERNS:
        matches = re.finditer(pattern, query)
        for match in matches:
            try:
                normalized = normalize_date_match(match, pattern_type)
                if normalized and normalized not in dates:
                    dates.append(normalized)
            except:
                continue

    return dates


def normalize_date_match(match, pattern_type: str) -> Optional[str]:
    """
    정규식 매칭 결과를 YYYY-MM-DD 형식으로 정규화

    Args:
        match: re.Match 객체
        pattern_type: 패턴 타입

    Returns:
        정규화된 날짜 문자열 (YYYY-MM-DD)
    """
    if pattern_type == 'compact':
        # 20241219 형식
        date_str = match.group(1)
        if len(date_str) == 8:
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
        else:
            return None
    else:
        # 나머지 형식들
        year, month, day = match.groups()[:3]

    # 날짜 유효성 검사
    try:
        datetime(int(year), int(month), int(day))
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    except ValueError:
        return None


def detect_court(query: str) -> Optional[Dict[str, str]]:
    """
    법원명 탐지

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 법원명 정보 또는 None
        {
            'input': '서울고법',
            'normalized_name': '서울고등법원',
            'is_alias': True
        }
    """
    query_lower = query.lower()

    # 정확히 일치하는 법원명 찾기
    for standard_name, aliases in COURT_ALIASES.items():
        for alias in aliases:
            if alias in query:
                return {
                    'input': alias,
                    'normalized_name': standard_name,
                    'is_alias': alias != standard_name
                }

    # 부분 일치 검색 (예: "서울" in "서울고법")
    for standard_name, aliases in COURT_ALIASES.items():
        for alias in aliases:
            if alias in query_lower or query_lower in alias:
                return {
                    'input': query,
                    'normalized_name': standard_name,
                    'is_alias': True
                }

    return None


def detect_customs(query: str) -> Optional[Dict[str, str]]:
    """
    처분청(세관) 탐지

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 세관명 정보 또는 None
        {
            'input': '인천공항',
            'normalized_name': '인천공항세관',
            'is_alias': True
        }
    """
    query_lower = query.lower()

    # 정확히 일치하는 세관명 찾기
    for standard_name, aliases in CUSTOMS_ALIASES.items():
        for alias in aliases:
            if alias in query:
                return {
                    'input': alias,
                    'normalized_name': standard_name,
                    'is_alias': alias != standard_name
                }

    # 부분 일치 검색
    for standard_name, aliases in CUSTOMS_ALIASES.items():
        for alias in aliases:
            if alias in query_lower or query_lower in alias:
                return {
                    'input': query,
                    'normalized_name': standard_name,
                    'is_alias': True
                }

    return None


def detect_all_patterns(query: str) -> Dict[str, any]:
    """
    모든 패턴 한번에 탐지

    Args:
        query: 사용자 입력 문자열

    Returns:
        탐지된 모든 패턴 정보
    """
    return {
        'case_number': detect_case_number(query),
        'precedent_number': detect_precedent_number(query),
        'dates': detect_date(query),
        'court': detect_court(query),
        'customs': detect_customs(query)
    }
