"""
날짜 탐지 테스트
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.pattern_detectors import detect_date
from utils.scoring import match_date_score


class TestDateDetection:
    """날짜 탐지 테스트"""

    @pytest.mark.parametrize("input_date,expected", [
        ("2024-12-19", ["2024-12-19"]),
        ("2024.12.19", ["2024-12-19"]),
        ("2024 12. 19", ["2024-12-19"]),
        ("2024년 12월 19일", ["2024-12-19"]),
        ("20241219", ["2024-12-19"]),
    ])
    def test_date_detection_various_formats(self, input_date, expected):
        """다양한 날짜 형식 탐지"""
        result = detect_date(input_date)
        assert result == expected

    def test_multiple_dates_in_text(self):
        """텍스트에 여러 날짜가 있는 경우"""
        query = "2024-01-15부터 2024-12-31까지"
        result = detect_date(query)
        assert len(result) == 2
        assert "2024-01-15" in result
        assert "2024-12-31" in result

    def test_date_matching_exact(self):
        """정확한 날짜 매칭"""
        query_date = "2024-12-19"
        target_date = "2024-12-19"
        score = match_date_score(query_date, target_date)
        assert score == 100.0

    def test_date_matching_different_format(self):
        """다른 형식이지만 같은 날짜"""
        query_dates = detect_date("2024.12.19")
        target_date = "2024-12-19"
        if query_dates:
            score = match_date_score(query_dates[0], target_date)
            assert score == 100.0

    def test_date_matching_year_month(self):
        """연월만 매칭"""
        query_date = "2024-12"
        target_date = "2024-12-19"
        score = match_date_score(query_date, target_date)
        assert score >= 70.0

    def test_date_matching_year_only(self):
        """연도만 매칭"""
        query_date = "2024"
        target_date = "2024-12-19"
        score = match_date_score(query_date, target_date)
        assert score >= 40.0

    def test_invalid_date(self):
        """잘못된 날짜"""
        result = detect_date("2024-13-32")  # 13월 32일은 존재하지 않음
        assert len(result) == 0

    def test_no_date_in_text(self):
        """날짜가 없는 텍스트"""
        result = detect_date("관세법 판례")
        assert len(result) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
