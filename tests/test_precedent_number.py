"""
판례번호 탐지 테스트
"""

import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.pattern_detectors import detect_precedent_number
from utils.scoring import match_precedent_number_score


class TestPrecedentNumberDetection:
    """판례번호 탐지 테스트"""

    def test_full_precedent_number(self):
        """완전한 판례번호 탐지"""
        query = "[대법원 2025. 2. 13. 선고 2023도1907 판결]"
        result = detect_precedent_number(query)
        assert result is not None
        assert result['court'] == "대법원"
        assert result['date'] == "2025-02-13"
        assert result['case_id'] == "2023도1907"
        assert result['full'] == "[대법원 2025. 2. 13. 선고 2023도1907 판결]"

    def test_simple_case_id(self):
        """간소화된 사건번호만 입력"""
        query = "2023도1907"
        result = detect_precedent_number(query)
        assert result is not None
        assert result['case_id'] == "2023도1907"
        assert result['full'] == "2023도1907"

    def test_precedent_number_with_different_date_format(self):
        """다른 날짜 형식"""
        query = "[서울고등법원 2024. 1. 26. 선고 2023노3408 판결]"
        result = detect_precedent_number(query)
        assert result is not None
        assert result['court'] == "서울고등법원"
        assert result['date'] == "2024-01-26"
        assert result['case_id'] == "2023노3408"

    def test_precedent_matching_score_simple(self):
        """판례번호 간단 매칭 점수"""
        query = "2023도1907"
        target = "[대법원 2025. 2. 13. 선고 2023도1907 판결]"
        score = match_precedent_number_score(query, target)
        assert score == 90.0

    def test_precedent_matching_score_full(self):
        """판례번호 완전 매칭 점수"""
        query = "[대법원 2025. 2. 13. 선고 2023도1907 판결]"
        target = "[대법원 2025. 2. 13. 선고 2023도1907 판결]"
        score = match_precedent_number_score(query, target)
        assert score == 100.0

    def test_different_case_ids(self):
        """다른 사건번호"""
        query = "2023도1907"
        target = "[대법원 2024. 4. 16. 선고 2021두36196 판결]"
        score = match_precedent_number_score(query, target)
        assert score == 0.0

    def test_case_id_in_text(self):
        """텍스트 중간에 사건번호"""
        query = "2023도1907 판례를 찾아주세요"
        result = detect_precedent_number(query)
        assert result is not None
        assert result['case_id'] == "2023도1907"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
