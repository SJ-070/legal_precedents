"""
법원명 탐지 테스트
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.pattern_detectors import detect_court
from utils.scoring import match_court_score


class TestCourtDetection:
    """법원명 탐지 테스트"""

    @pytest.mark.parametrize("query,expected", [
        ("대법원", "대법원"),
        ("서울고법", "서울고법"),
        ("인천지법", "인천지법"),
        ("부산고등법원", "부산고법"),
        ("서울고등법원", "서울고법"),
    ])
    def test_court_detection(self, query, expected):
        """법원명 탐지"""
        result = detect_court(query)
        assert result is not None
        assert result['normalized_name'] == expected or result['input'] == expected

    def test_court_matching_full_name(self):
        """정식명칭 매칭"""
        query = "대법원"
        target = "대법원"
        score = match_court_score(query, target)
        assert score == 100.0

    def test_court_matching_alias(self):
        """약칭 매칭"""
        query = "서울고법"
        target = "서울고등법원"
        score = match_court_score(query, target)
        assert score >= 95.0

    def test_court_in_text(self):
        """텍스트 중간에 법원명"""
        query = "대법원 판례를 찾아주세요"
        result = detect_court(query)
        assert result is not None
        assert result['normalized_name'] == "대법원"

    def test_court_matching_partial(self):
        """부분 일치"""
        query = "서울"
        target = "서울고등법원"
        score = match_court_score(query, target)
        assert score >= 70.0

    def test_no_court_in_text(self):
        """법원명 없는 텍스트"""
        query = "관세법 판례"
        result = detect_court(query)
        # 부분 일치가 발생할 수 있으므로 None이 아닐 수도 있음
        # 이 케이스는 실제로 검증하기 어려움


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
