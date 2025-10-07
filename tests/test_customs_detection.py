"""
처분청(세관) 탐지 테스트
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.pattern_detectors import detect_customs
from utils.scoring import match_customs_score


class TestCustomsDetection:
    """처분청(세관) 탐지 테스트"""

    @pytest.mark.parametrize("query,expected", [
        ("인천공항", "인천공항세관"),
        ("인천공항세관", "인천공항세관"),
        ("대전세관", "대전세관"),
        ("부산세관", "부산세관"),
    ])
    def test_customs_detection(self, query, expected):
        """세관명 탐지"""
        result = detect_customs(query)
        assert result is not None
        assert result['normalized_name'] == expected

    def test_customs_matching_full_name(self):
        """정식명칭 매칭"""
        query = "대전세관"
        target = "대전세관"
        score = match_customs_score(query, target)
        assert score == 100.0

    def test_customs_matching_alias(self):
        """약칭 매칭"""
        query = "인천공항"
        target = "인천공항세관"
        score = match_customs_score(query, target)
        assert score == 95.0

    def test_customs_in_text(self):
        """텍스트 중간에 세관명"""
        query = "인천공항세관 관련 판례"
        result = detect_customs(query)
        assert result is not None
        assert result['normalized_name'] == "인천공항세관"

    def test_no_customs_in_text(self):
        """세관명 없는 텍스트"""
        query = "관세법 판례"
        result = detect_customs(query)
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
