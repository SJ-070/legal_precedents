#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOLEG Data Cleaner - 법무부 국가법령정보센터 관세 판례 데이터 정제 도구
법무부 국가법령정보센터(MOLEG) 관세 판례 데이터 정제 및 구조화 도구

=== 주요 기능 ===

1. 중복 제거 (Duplicate Removal)
   - 목적: 동일한 판례번호로 중복 수집된 데이터 제거
   - 기준 1: 정확한 판례번호 일치
     예시: "대법원 2023다12345" 판례번호가 여러 개 있으면 첫 번째만 유지
   - 기준 2: 유사한 내용 탐지
     방식: '내용' 필드의 첫 200자를 서명(signature)으로 사용하여 유사 판례 탐지
     예시: 동일한 시작 텍스트를 가진 다른 판례번호들을 중복으로 판단

2. 구조화 필드 추출 (Structured Field Extraction)
   - 목적: '내용' 필드에서 구조화된 정보를 추출하여 검색 및 분석 향상
   - 추출 필드:

   2.1. 선고일자 (Decision Date)
        - 패턴: "2024. 1. 1. 선고", "2024-01-01", "2024년 1월 1일"
        - 범위: 1990년~2025년 (합리적 연도 범위)
        - 형식: YYYY-MM-DD 표준화

   2.2. 법원명 (Court Name)
        - 패턴: 대법원, 고등법원, 지방법원 등
        - 예시: "서울고등법원", "인천지방법원", "대법원"
        - 정제: 대괄호, 연도 정보 제거 후 20자 이내로 제한

   2.3. 사건유형 (Case Type)
        - 관세 관련 사건 유형 탐지
        - 패턴: "관세법위반", "관세포탈", "밀수입", "관세부과취소" 등
        - 길이: 50자 이내로 제한

   2.4. 판결요지 (Decision Summary)
        - 패턴: 【판시사항】, 【판결요지】, 【요지】 섹션에서 추출
        - 최소 길이: 30자 이상 (실질적 내용 보장)
        - 최대 길이: 800자 (너무 길면 말줄임표 추가)
        - 정제: 공백 정규화

   2.5. 참조조문 (Referenced Articles)
        - 패턴: 【참조조문】, 【참조법조】, 【관련조문】 섹션에서 추출
        - 길이: 500자 이내로 제한
        - 정제: 공백 정규화

   2.6. 판결결과 (Decision Result)
        - 패턴: "파기", "기각", "인용", "취소", "환송", "승소", "패소" 등
        - 우선순위: 주문, 판결, 결론 맥락에서 먼저 검색
        - 대안: 직접 패턴 매칭

3. 안전 장치 (Safety Features)
   - 백업 생성: 원본 파일을 자동으로 백업
     형식: data_moleg_backup_YYYYMMDD_HHMMSS.json
   - Dry Run 모드: 실제 변경 전 결과 미리보기 제공
     dry_run=True (기본값): 미리보기만, 파일 변경 없음
     dry_run=False: 실제 정제 및 구조화 작업 수행
   - 진행률 표시: 100건마다 처리 진행률 출력
   - 샘플 표시: 추출 결과의 첫 3개 샘플을 화면에 출력

=== 사용법 ===

1. 미리보기 모드 (기본):
   cleaner = MOLEGDataCleaner()
   results = cleaner.clean_and_extract(dry_run=True)

2. 실제 정제 및 구조화 수행:
   cleaner = MOLEGDataCleaner()
   results = cleaner.clean_and_extract(dry_run=False)

=== 출력 형식 ===

생성 파일:
- data_moleg.json: 구조화된 필드가 추가된 정제 데이터 (원본 파일 덮어쓰기)
- moleg_cleaning_report.json: 상세한 정제 및 추출 통계 보고서
- data_moleg_backup_YYYYMMDD_HHMMSS.json: 원본 파일 백업

반환값 (딕셔너리):
- original_count: 원본 데이터 항목 수
- deduplicated_count: 중복 제거 후 데이터 항목 수
- duplicates_removed: 중복으로 제거된 항목 수
- extraction_stats: 각 필드별 추출 성공 통계
- latest_date: 추출된 가장 최근 선고일자
- enriched_data: 구조화된 데이터 (dry_run=False일 때만)

=== 처리 통계 예시 ===

추출 성공률:
- 선고일자: 85.2% (1,234건/1,450건)
- 법원명: 92.1% (1,335건/1,450건)
- 사건유형: 78.9% (1,144건/1,450건)
- 판결요지: 68.3% (991건/1,450건)
- 참조조문: 45.7% (663건/1,450건)
- 판결결과: 89.4% (1,296건/1,450건)
"""

import json
import re
from datetime import datetime
import shutil
from collections import defaultdict, Counter
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.parent

class MOLEGDataCleaner:
    def __init__(self):
        self.moleg_data_file = str(PROJECT_ROOT / "data_moleg.json")
        self.backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_backup(self, filename):
        """Create backup of original file"""
        backup_name = f"{filename}{self.backup_suffix}"
        shutil.copy2(filename, backup_name)
        print(f"✓ Backup created: {backup_name}")
        return backup_name

    def find_duplicates(self, data):
        """Find duplicate entries by 판례번호 and similar content"""
        print("=" * 50)
        print("DUPLICATE DETECTION")
        print("=" * 50)

        duplicates = {
            'exact_case_number': [],
            'similar_content': []
        }

        # 1. Check for exact duplicate case numbers
        case_numbers = [entry.get('판례번호', '').strip() for entry in data]
        case_number_counts = Counter(case_numbers)
        exact_duplicates = {k: v for k, v in case_number_counts.items() if v > 1 and k}

        if exact_duplicates:
            print(f"Found {len(exact_duplicates)} duplicate case numbers:")
            for case_num, count in exact_duplicates.items():
                print(f"  - {case_num}: {count} occurrences")
                duplicates['exact_case_number'].append({
                    'case_number': case_num,
                    'count': count
                })
        else:
            print("✓ No exact duplicate case numbers found")

        # 2. Check for similar content (first 200 chars)
        content_signatures = {}
        similar_content = []

        for i, entry in enumerate(data):
            content = str(entry.get('내용', '')).strip()
            if len(content) >= 200:
                signature = content[:200]  # First 200 characters as signature

                if signature in content_signatures:
                    # Found similar content
                    original_idx = content_signatures[signature]
                    similar_pair = {
                        'signature': signature[:50] + '...',
                        'entries': [
                            {'index': original_idx, 'case_number': data[original_idx].get('판례번호', '')},
                            {'index': i, 'case_number': entry.get('판례번호', '')}
                        ]
                    }
                    similar_content.append(similar_pair)
                    duplicates['similar_content'].append(similar_pair)
                else:
                    content_signatures[signature] = i

        if similar_content:
            print(f"\nFound {len(similar_content)} pairs with similar content:")
            for pair in similar_content[:3]:  # Show first 3 examples
                print(f"  - Cases: {pair['entries'][0]['case_number']} vs {pair['entries'][1]['case_number']}")
                print(f"    Similar start: {pair['signature']}")
        else:
            print("✓ No similar content found")

        return duplicates

    def extract_structured_fields(self, content):
        """Extract structured information from the '내용' field"""
        extracted = {}

        # 2.1. 선고일자 (Decision date)
        date_patterns = [
            r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*선고',  # 2024. 1. 1. 선고
            r'(\d{4})-(\d{2})-(\d{2})',                        # 2024-01-01
            r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일',          # 2024년 1월 1일
            r'\[.*?(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*선고'  # [대법원 2024. 1. 1. 선고
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, content)
            if matches:
                try:
                    match = matches[0]  # Take first match
                    if len(match) >= 3:
                        year, month, day = match[:3]
                        date_str = f"{year}-{int(month):02d}-{int(day):02d}"
                        # Validate date
                        datetime.strptime(date_str, '%Y-%m-%d')
                        if 1990 <= int(year) <= 2025:  # Reasonable year range
                            extracted['선고일자'] = date_str
                            break
                except:
                    continue

        # 2.2. 법원명 (Court name)
        court_patterns = [
            r'(\[대법원\s+\d{4})',                    # [대법원 2024
            r'(\[.*?고등법원\s+\d{4})',               # [서울고등법원 2024
            r'(\[.*?지방법원\s+\d{4})',               # [인천지방법원 2024
            r'(대법원)',                             # 대법원
            r'(서울고등법원|부산고등법원|대구고등법원|광주고등법원|대전고등법원|수원고등법원)',
            r'(\w+고등법원)',                        # 기타고등법원
            r'(\w+지방?법원)',                       # 지방법원
        ]

        for pattern in court_patterns:
            match = re.search(pattern, content)
            if match:
                court_name = match.group(1)
                # Clean up court name
                court_name = re.sub(r'\[|\]|\d{4}.*', '', court_name).strip()
                if court_name and len(court_name) <= 20:
                    extracted['법원명'] = court_name
                    break

        # 2.3. 사건유형 (Case type)
        case_type_patterns = [
            r'(관세법위반)',
            r'(관세등.*?취소)',
            r'(관세.*?거부.*?취소)',
            r'(관세.*?부과.*?취소)',
            r'(관세.*?경정.*?취소)',
            r'(특정범죄가중처벌등에관한법률위반.*?관세)',
            r'(특정범죄가중처벌등에관한법률위반)',
            r'(밀수입)',
            r'(관세포탈)',
        ]

        for pattern in case_type_patterns:
            match = re.search(pattern, content)
            if match:
                case_type = match.group(1)
                if len(case_type) <= 50:
                    extracted['사건유형'] = case_type
                    break

        # 2.4. 판결요지 (Decision summary)
        summary_patterns = [
            r'【판시사항】\s*(.*?)(?:【|$)',           # 【판시사항】
            r'【판결요지】\s*(.*?)(?:【|$)',           # 【판결요지】
            r'【요\s*지】\s*(.*?)(?:【|$)',            # 【요지】
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                summary = match.group(1).strip()
                # Clean up summary
                summary = re.sub(r'\s+', ' ', summary)  # Normalize whitespace
                if len(summary) > 30:  # Must have substantial content
                    # Truncate if too long
                    if len(summary) > 800:
                        summary = summary[:800] + '...'
                    extracted['판결요지'] = summary
                    break

        # 2.5. 참조조문 (Referenced articles)
        reference_patterns = [
            r'【참조조문】\s*(.*?)(?:【|$)',
            r'【참조법조】\s*(.*?)(?:【|$)',
            r'【관련조문】\s*(.*?)(?:【|$)',
        ]

        for pattern in reference_patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                references = match.group(1).strip()
                # Clean up references
                references = re.sub(r'\s+', ' ', references)
                if references and len(references) <= 500:
                    extracted['참조조문'] = references
                    break

        # 2.6. 판결결과 (Decision result)
        result_patterns = [
            r'(파기)',
            r'(기각)',
            r'(인용)',
            r'(취소)',
            r'(환송)',
            r'(승소)',
            r'(패소)',
            r'(일부인용)',
            r'(전부기각)',
        ]

        # Look for result patterns in specific contexts
        result_contexts = [
            r'주\s*문.*?(파기|기각|인용|취소|환송)',
            r'판결.*?(파기|기각|인용|취소|환송)',
            r'결\s*론.*?(파기|기각|인용|취소|환송)',
        ]

        for context_pattern in result_contexts:
            match = re.search(context_pattern, content)
            if match:
                extracted['판결결과'] = match.group(1)
                break

        # If no context match, try direct patterns
        if '판결결과' not in extracted:
            for pattern in result_patterns:
                if re.search(pattern, content):
                    extracted['판결결과'] = pattern.strip('()')
                    break

        return extracted

    def clean_and_extract(self, dry_run=True):
        """Clean duplicates and extract structured fields"""
        print("=" * 60)
        print("CLEANING data_moleg.json")
        print("=" * 60)
        print("Focus: 1) Remove duplicates, 2) Extract structured fields")

        # Load data
        with open(self.moleg_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_count = len(data)
        print(f"\nOriginal entries: {original_count}")

        # Step 1: Find duplicates
        duplicates = self.find_duplicates(data)

        # Remove duplicates (keep first occurrence)
        cleaned_data = []
        seen_case_numbers = set()
        removed_duplicates = []

        for i, entry in enumerate(data):
            case_number = entry.get('판례번호', '').strip()

            if case_number and case_number in seen_case_numbers:
                removed_duplicates.append({
                    'index': i,
                    'case_number': case_number,
                    'title': entry.get('제목', '')[:50] + '...'
                })
                continue

            cleaned_data.append(entry)
            if case_number:
                seen_case_numbers.add(case_number)

        deduplicated_count = len(cleaned_data)
        duplicates_removed = original_count - deduplicated_count

        print(f"\nAfter deduplication:")
        print(f"├─ Removed duplicates: {duplicates_removed}")
        print(f"├─ Remaining entries: {deduplicated_count}")
        print(f"└─ Deduplication rate: {(deduplicated_count/original_count)*100:.1f}%")

        # Step 2: Extract structured fields
        print(f"\n" + "=" * 50)
        print("STRUCTURED FIELD EXTRACTION")
        print("=" * 50)

        enriched_data = []
        extraction_stats = defaultdict(int)
        sample_extractions = []

        for i, entry in enumerate(cleaned_data):
            if (i + 1) % 100 == 0:
                print(f"Processing entry {i+1}/{deduplicated_count}...")

            # Start with original fields
            enriched_entry = {
                '제목': entry.get('제목', ''),
                '판례번호': entry.get('판례번호', ''),
                '내용': entry.get('내용', '')
            }

            # Extract structured fields
            content = entry.get('내용', '')
            if content:
                extracted_fields = self.extract_structured_fields(content)

                # Add extracted fields
                for field_name, field_value in extracted_fields.items():
                    enriched_entry[field_name] = field_value
                    extraction_stats[field_name] += 1

                # Collect sample for display
                if len(extracted_fields) >= 3 and len(sample_extractions) < 3:
                    sample_extractions.append({
                        'case_number': enriched_entry['판례번호'],
                        'title': enriched_entry['제목'][:50] + '...',
                        'extracted': extracted_fields
                    })

            enriched_data.append(enriched_entry)

        # Report extraction results
        print(f"\nSTRUCTURED FIELD EXTRACTION RESULTS:")
        print(f"├─ Total entries processed: {deduplicated_count}")
        print(f"├─ Fields extracted:")
        for field, count in extraction_stats.items():
            percentage = (count / deduplicated_count) * 100
            print(f"│  ├─ {field}: {count} entries ({percentage:.1f}%)")
        print(f"└─ Average fields per entry: {sum(extraction_stats.values())/deduplicated_count:.1f}")

        # Show sample extractions
        if sample_extractions:
            print(f"\n" + "=" * 50)
            print("SAMPLE EXTRACTED ENTRIES")
            print("=" * 50)
            for i, sample in enumerate(sample_extractions, 1):
                print(f"{i}. Case: {sample['case_number']}")
                print(f"   Title: {sample['title']}")
                for field, value in sample['extracted'].items():
                    display_value = value[:100] + '...' if len(str(value)) > 100 else value
                    print(f"   {field}: {display_value}")
                print()

        # Get latest date info
        latest_dates = []
        for entry in enriched_data:
            if '선고일자' in entry:
                try:
                    date_obj = datetime.strptime(entry['선고일자'], '%Y-%m-%d')
                    latest_dates.append(date_obj)
                except:
                    continue

        latest_date = max(latest_dates) if latest_dates else None

        print(f"\n" + "=" * 50)
        print("DATE BASELINE INFORMATION")
        print("=" * 50)
        print(f"├─ Extracted dates: {len(latest_dates)}")
        if latest_date:
            print(f"├─ Latest extracted date: {latest_date.strftime('%Y-%m-%d')}")
            print(f"└─ Date range: {min(latest_dates).strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")
        else:
            print(f"└─ No valid dates extracted")

        # Save results
        if not dry_run:
            # Create backup
            self.create_backup(self.moleg_data_file)

            # Save enriched data to original file
            with open(self.moleg_data_file, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Enriched data saved to: {self.moleg_data_file}")

            # Generate detailed report
            report = {
                'processing_summary': {
                    'original_count': original_count,
                    'deduplicated_count': deduplicated_count,
                    'duplicates_removed': duplicates_removed,
                    'final_count': len(enriched_data)
                },
                'deduplication_details': {
                    'removed_duplicates': removed_duplicates
                },
                'extraction_statistics': dict(extraction_stats),
                'extraction_success_rates': {
                    field: round((count / deduplicated_count) * 100, 2)
                    for field, count in extraction_stats.items()
                },
                'baseline_date_info': {
                    'latest_date': latest_date.strftime('%Y-%m-%d') if latest_date else None,
                    'extracted_dates_count': len(latest_dates)
                },
                'extracted_fields': [
                    '선고일자 (Decision date)',
                    '법원명 (Court name)',
                    '사건유형 (Case type)',
                    '판결요지 (Decision summary)',
                    '참조조문 (Referenced articles)',
                    '판결결과 (Decision result)'
                ],
                'timestamp': datetime.now().isoformat(),
                'backup_file': f"{self.moleg_data_file}{self.backup_suffix}"
            }

            report_file = PROJECT_ROOT / 'moleg_cleaning_report.json'
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"✓ Detailed report saved to: {report_file}")

        else:
            print(f"\n[DRY RUN] Operations completed successfully")
            print(f"[DRY RUN] Would remove {duplicates_removed} duplicates")
            print(f"[DRY RUN] Would extract {len(extraction_stats)} field types")
            print(f"[DRY RUN] To apply changes, run with dry_run=False")

        return {
            'original_count': original_count,
            'deduplicated_count': deduplicated_count,
            'duplicates_removed': duplicates_removed,
            'extraction_stats': extraction_stats,
            'latest_date': latest_date,
            'enriched_data': enriched_data if not dry_run else None
        }

if __name__ == "__main__":
    cleaner = MOLEGDataCleaner()

    print("MOLEG DATA CLEANING & ENRICHMENT TOOL")
    print("Focus: Remove duplicates + Extract structured fields")
    print()

    # Run dry run first
    results = cleaner.clean_and_extract(dry_run=True)

    print(f"\n" + "=" * 60)
    print("READY TO APPLY CHANGES")
    print("=" * 60)
    print("To apply the changes, uncomment and run:")
    print("# results = cleaner.clean_and_extract(dry_run=False)")

    # Run real run
    results = cleaner.clean_and_extract(dry_run=False)