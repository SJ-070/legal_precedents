#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KCS Data Cleaner - Simplified Version
한국관세청(KCS) 법원 판례 데이터 정제 도구

=== 주요 기능 ===

1. 최소 콘텐츠 필터링 (Minimal Content Removal)
   - 목적: 실질적인 내용이 없는 빈 데이터 제거
   - 기준: 핵심 필드의 총 글자 수 < 20자
   - 대상 필드: ['판결주문', '청구취지', '판결이유']
   - 작업 방식: 세 필드의 텍스트 길이를 합쳐서 20자 미만이면 삭제

   예시:
     판결주문: "기각" (2자)
     청구취지: "승소" (2자)
     판결이유: "근거없음" (4자)
     총합: 8자 → 삭제됨

2. 중복 제거 (Duplicate Removal)
   - 목적: 크롤링 과정에서 발생한 중복 데이터 제거
   - 기준: 동일한 '사건번호' 필드값
   - 작업 방식: 같은 사건번호가 여러 개 있으면 첫 번째만 유지, 나머지 삭제

   예시:
     사건번호: "2023구합12345" → 첫 번째 항목만 유지
     사건번호: "2023구합12345" → 삭제됨

3. 안전 장치 (Safety Features)
   - 백업 생성: 원본 파일을 자동으로 백업
     형식: data_kcs_backup_YYYYMMDD_HHMMSS.json
   - Dry Run 모드: 실제 변경 전 결과 미리보기 제공
     dry_run=True (기본값): 미리보기만, 파일 변경 없음
     dry_run=False: 실제 정제 작업 수행
   - 로깅: 모든 정제 과정과 결과를 콘솔에 출력
     (제거된 항목 수, 보존율 등 통계 정보 포함)

=== 사용법 ===

1. 미리보기 모드 (기본):
   cleaner = KCSDataCleaner()
   results = cleaner.clean_kcs_data(dry_run=True)

2. 실제 정제 수행:
   cleaner = KCSDataCleaner()
   results = cleaner.clean_kcs_data(dry_run=False)

=== 출력 형식 ===

반환값 (딕셔너리):
- original_count: 원본 데이터 항목 수
- cleaned_count: 정제 후 데이터 항목 수
- removed_minimal: 최소 콘텐츠로 제거된 항목 수
- removed_duplicates: 중복으로 제거된 항목 수
- cleaned_data: 정제된 데이터 (dry_run=False일 때만)
"""

import json
from datetime import datetime
import shutil
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

class KCSDataCleaner:
    def __init__(self):
        self.kcs_data_file = str(PROJECT_ROOT / "data_kcs.json")
        self.backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_backup(self, filename):
        """Create backup of original file"""
        backup_name = f"{filename}{self.backup_suffix}"
        shutil.copy2(filename, backup_name)
        print(f"✓ Backup created: {backup_name}")
        return backup_name

    def clean_kcs_data(self, dry_run=True):
        """
        Clean data_kcs.json with essential criteria only:
        1. Remove entries with total content < 20 characters in key fields
        2. Remove exact duplicates (keep first occurrence)
        """
        print("=" * 50)
        print("KCS 데이터 정제 - 핵심 기능만")
        print("=" * 50)

        # Load data
        with open(self.kcs_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_count = len(data)
        print(f"원본 항목 수: {original_count}")

        cleaned_data = []
        seen_case_numbers = set()
        removed_minimal = 0
        removed_duplicates = 0

        key_fields = ['판결주문', '청구취지', '판결이유']

        print(f"\n정제 기준:")
        print(f"1. 핵심 필드 총 글자 수 < 20자 제거")
        print(f"2. 중복 사건번호 제거 (첫 번째만 유지)")

        for entry in data:
            case_number = entry.get('사건번호', '').strip()

            # 1. 최소 콘텐츠 확인
            total_content_length = 0
            for field in key_fields:
                content = str(entry.get(field, '')).strip()
                total_content_length += len(content)

            if total_content_length < 20:
                removed_minimal += 1
                continue

            # 2. 중복 확인
            if case_number and case_number in seen_case_numbers:
                removed_duplicates += 1
                continue

            # 정제된 데이터에 추가
            cleaned_data.append(entry)
            if case_number:
                seen_case_numbers.add(case_number)

        cleaned_count = len(cleaned_data)
        removed_count = original_count - cleaned_count

        # 결과 출력
        print(f"\n" + "=" * 30)
        print("정제 결과")
        print("=" * 30)
        print(f"최소 콘텐츠 제거: {removed_minimal}건")
        print(f"중복 제거: {removed_duplicates}건")
        print(f"총 제거: {removed_count}건")
        print(f"최종 데이터: {cleaned_count}건")
        print(f"보존율: {(cleaned_count/original_count)*100:.1f}%")

        # 데이터 저장
        if not dry_run:
            # 백업 생성
            self.create_backup(self.kcs_data_file)

            # 정제된 데이터 저장
            with open(self.kcs_data_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 정제된 데이터가 {self.kcs_data_file}에 저장되었습니다")

        else:
            print(f"\n[미리보기] {removed_count}건이 제거될 예정입니다")
            print(f"[미리보기] 실제 적용하려면 dry_run=False로 실행하세요")

        return {
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'removed_minimal': removed_minimal,
            'removed_duplicates': removed_duplicates,
            'cleaned_data': cleaned_data if not dry_run else None
        }

if __name__ == "__main__":
    cleaner = KCSDataCleaner()

    print("KCS 데이터 정제 도구 - 간소화 버전")
    print()

    # 미리보기 실행
    print("미리보기 모드로 실행 중...")
    results = cleaner.clean_kcs_data(dry_run=True)

    print(f"\n" + "=" * 40)
    print("실제 적용하겠습니다.")
    results = cleaner.clean_kcs_data(dry_run=False)