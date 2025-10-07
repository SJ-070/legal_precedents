"""
사건번호 탐지 테스트
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.pattern_detectors import detect_case_number
from utils.scoring import match_case_number_score


class TestCaseNumberDetection:
    """사건번호 탐지 테스트"""

    def test_full_case_number(self):
        """완전한 사건번호 탐지"""
        query = "대전지법2023구합208027"
        result = detect_case_number(query)
        assert result is not None
        assert result['court'] == "대전지법"
        assert result['year'] == "2023"
        assert result['type'] == "구합"
        assert result['number'] == "208027"
        assert result['full'] == "대전지법2023구합208027"

    def test_partial_case_number_without_court(self):
        """부분 사건번호 탐지 (법원명 생략)"""
        query = "2023구합208027"
        result = detect_case_number(query)
        assert result is not None
        assert result['court'] == ""
        assert result['year'] == "2023"
        assert result['type'] == "구합"
        assert result['number'] == "208027"

    def test_case_number_with_text(self):
        """텍스트 중간에 사건번호가 있는 경우"""
        query = "인천지법2023구합58668 관련 판례를 찾아줘"
        result = detect_case_number(query)
        assert result is not None
        assert result['court'] == "인천지법"
        assert result['year'] == "2023"

    def test_case_number_matching_score_full(self):
        """사건번호 완전 매칭 점수 테스트"""
        query = "대전지법2023구합208027"
        target = "대전지법2023구합208027"
        score = match_case_number_score(query, target)
        assert score == 100.0

    def test_case_number_matching_score_partial(self):
        """사건번호 부분 매칭 점수 테스트 (법원명 제외)"""
        query = "2023구합208027"
        target = "대전지법2023구합208027"
        score = match_case_number_score(query, target)
        assert score == 85.0

    def test_case_number_matching_score_with_court(self):
        """법원명 포함 부분 매칭"""
        query = "인천지법2023구합58668"
        target = "인천지법2023구합58668"
        score = match_case_number_score(query, target)
        assert score == 100.0

    def test_no_case_number(self):
        """사건번호 없는 입력"""
        query = "관세법 판례"
        result = detect_case_number(query)
        assert result is None

    def test_invalid_case_number(self):
        """잘못된 형식의 사건번호"""
        query = "ABC123"
        result = detect_case_number(query)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
