"""
통합 검색 테스트
"""

import pytest
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.precedent_search import search_precedent, format_precedent_title


# 테스트용 샘플 데이터
SAMPLE_KCS_DATA = [
    {
        "사건명": "경정청구거부처분취소",
        "사건번호": "대전지법2023구합208027",
        "선고일자\n(종결일자)": "2024-12-19",
        "결과": "국가승",
        "처분청": "대전세관"
    },
    {
        "사건명": "관세등경정거부처분취소",
        "사건번호": "인천지법2023구합58668",
        "선고일자\n(종결일자)": "2024-12-12",
        "결과": "국가승",
        "처분청": "인천공항세관"
    }
]

SAMPLE_MOLEG_DATA = [
    {
        "제목": "관세법위반·의료기기법위반",
        "판례번호": "[대법원 2025. 2. 13. 선고 2023도1907 판결]",
        "선고일자": "2025-02-13",
        "법원명": "대법원",
        "사건유형": "관세법위반"
    },
    {
        "제목": "관세등부과처분취소",
        "판례번호": "[대법원 2024. 4. 16. 선고 2021두36196 판결]",
        "선고일자": "2024-04-16",
        "법원명": "대법원",
        "사건유형": "관세등부과처분취소"
    }
]


class TestIntegrationSearch:
    """통합 검색 테스트"""

    def test_search_with_case_number(self):
        """사건번호로 검색"""
        query = "2023구합208027"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        assert results[0]['score'] >= 85.0
        assert results[0]['source'] == 'kcs'

    def test_search_with_precedent_number(self):
        """판례번호로 검색"""
        query = "2023도1907"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        assert results[0]['score'] >= 90.0
        assert results[0]['source'] == 'moleg'

    def test_search_with_date(self):
        """날짜로 검색"""
        query = "2024-12-19"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        # 날짜만으로는 여러 결과가 나올 수 있음

    def test_search_with_court_name(self):
        """법원명으로 검색"""
        query = "대법원"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        # MOLEG 데이터에서 법원명 매칭
        moleg_results = [r for r in results if r['source'] == 'moleg']
        assert len(moleg_results) > 0

    def test_search_with_customs(self):
        """세관명으로 검색"""
        query = "인천공항세관"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        assert results[0]['source'] == 'kcs'

    def test_search_with_multiple_keywords(self):
        """복합 키워드 검색"""
        query = "대법원 2023도1907 2025-02-13"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) > 0
        # 복합 키워드는 높은 점수를 받아야 함
        assert results[0]['score'] >= 90.0

    def test_search_ranking(self):
        """검색 결과 점수 순 정렬 확인"""
        query = "2024"  # 연도만 검색
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        # 점수가 내림차순으로 정렬되어 있는지 확인
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_with_kcs_and_moleg(self):
        """KCS와 MOLEG 데이터 동시 검색"""
        query = "관세"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA, min_score=0)
        # 두 데이터 소스에서 모두 결과가 나올 수 있음
        sources = set(r['source'] for r in results)
        # 최소한 하나는 있어야 함
        assert len(sources) > 0

    def test_format_precedent_title_kcs(self):
        """KCS 제목 포맷팅"""
        result = {
            'source': 'kcs',
            'score': 100.0,
            'data': SAMPLE_KCS_DATA[0]
        }
        title = format_precedent_title(result)
        assert "대전지법2023구합208027" in title
        assert "경정청구거부처분취소" in title

    def test_format_precedent_title_moleg(self):
        """MOLEG 제목 포맷팅"""
        result = {
            'source': 'moleg',
            'score': 100.0,
            'data': SAMPLE_MOLEG_DATA[0]
        }
        title = format_precedent_title(result)
        assert "2023도1907" in title
        assert "관세법위반" in title

    def test_no_results_for_irrelevant_query(self):
        """무관한 검색어로 검색"""
        query = "xyz123abc"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA)
        assert len(results) == 0

    def test_min_score_threshold(self):
        """최소 점수 임계값 테스트"""
        query = "2024"
        results = search_precedent(query, SAMPLE_KCS_DATA, SAMPLE_MOLEG_DATA, min_score=50.0)
        # 모든 결과가 최소 점수 이상이어야 함
        for result in results:
            assert result['score'] >= 50.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
