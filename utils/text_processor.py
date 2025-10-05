"""
Text Processing Utilities
텍스트 전처리 및 추출 모듈
"""

import re


def preprocess_text(text):
    """텍스트 정규화 및 전처리"""
    if not text or not isinstance(text, str):
        return ""
    # 공백 정규화 및 특수문자 처리
    text = re.sub(r'\s+', ' ', text)  # 여러 공백을 하나로
    text = text.strip()  # 앞뒤 공백 제거
    return text


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
