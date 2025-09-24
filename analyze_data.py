#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legal Precedents Data Analysis Tool
Analyzes the existing JSON files to establish cleaning criteria and data quality metrics
"""

import json
import pandas as pd
from datetime import datetime
import re
from collections import Counter, defaultdict

class LegalDataAnalyzer:
    def __init__(self):
        self.kcs_data_file = "data_kcs.json"
        self.moleg_data_file = "data_moleg.json"

    def analyze_court_cases(self):
        """Analyze data_kcs.json file for data quality and cleaning criteria"""
        print("=" * 60)
        print("ANALYZING data_kcs.json")
        print("=" * 60)

        with open(self.kcs_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_entries = len(data)
        print(f"Total entries: {total_entries}")

        # Analyze data structure
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            print(f"\nData structure keys: {keys}")

        # Field completion analysis
        field_stats = {}
        for key in keys:
            filled = sum(1 for item in data if item.get(key) and str(item.get(key)).strip())
            empty = total_entries - filled
            field_stats[key] = {
                'filled': filled,
                'empty': empty,
                'fill_rate': (filled / total_entries) * 100
            }

        print("\n" + "=" * 40)
        print("FIELD COMPLETION ANALYSIS")
        print("=" * 40)
        for field, stats in field_stats.items():
            print(f"{field}:")
            print(f"  - Filled: {stats['filled']} ({stats['fill_rate']:.1f}%)")
            print(f"  - Empty: {stats['empty']} ({100-stats['fill_rate']:.1f}%)")

        # Content length analysis for key fields
        key_fields = ['판결주문', '청구취지', '판결이유']
        content_stats = {}

        print("\n" + "=" * 40)
        print("CONTENT LENGTH ANALYSIS")
        print("=" * 40)

        for field in key_fields:
            lengths = []
            empty_count = 0
            very_short = 0  # < 10 characters
            short = 0       # 10-100 characters
            medium = 0      # 100-500 characters
            long = 0        # > 500 characters

            for item in data:
                content = str(item.get(field, '')).strip()
                if not content:
                    empty_count += 1
                    lengths.append(0)
                else:
                    length = len(content)
                    lengths.append(length)
                    if length < 10:
                        very_short += 1
                    elif length < 100:
                        short += 1
                    elif length < 500:
                        medium += 1
                    else:
                        long += 1

            content_stats[field] = {
                'empty': empty_count,
                'very_short': very_short,
                'short': short,
                'medium': medium,
                'long': long,
                'avg_length': sum(lengths) / len(lengths) if lengths else 0,
                'max_length': max(lengths) if lengths else 0
            }

            print(f"\n{field}:")
            print(f"  - Empty: {empty_count}")
            print(f"  - Very short (<10): {very_short}")
            print(f"  - Short (10-100): {short}")
            print(f"  - Medium (100-500): {medium}")
            print(f"  - Long (>500): {long}")
            print(f"  - Average length: {content_stats[field]['avg_length']:.1f}")
            print(f"  - Max length: {content_stats[field]['max_length']}")

        # Date analysis
        print("\n" + "=" * 40)
        print("DATE ANALYSIS")
        print("=" * 40)

        date_field = '선고일자\n(종결일자)'
        dates = []
        invalid_dates = 0

        for item in data:
            date_str = str(item.get(date_field, '')).strip()
            if date_str:
                try:
                    # Try to parse various date formats
                    if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        dates.append(date_obj)
                    else:
                        invalid_dates += 1
                except:
                    invalid_dates += 1

        if dates:
            latest_date = max(dates)
            earliest_date = min(dates)
            print(f"Valid dates: {len(dates)}")
            print(f"Invalid dates: {invalid_dates}")
            print(f"Latest date: {latest_date.strftime('%Y-%m-%d')}")
            print(f"Earliest date: {earliest_date.strftime('%Y-%m-%d')}")

            # Year distribution
            year_dist = Counter(date.year for date in dates)
            print(f"\nYear distribution:")
            for year in sorted(year_dist.keys(), reverse=True)[:5]:
                print(f"  - {year}: {year_dist[year]} cases")

        # Duplicate analysis
        print("\n" + "=" * 40)
        print("DUPLICATE ANALYSIS")
        print("=" * 40)

        # Check for exact duplicates by case number
        case_numbers = [item.get('사건번호', '') for item in data if item.get('사건번호')]
        case_number_counts = Counter(case_numbers)
        duplicates = {k: v for k, v in case_number_counts.items() if v > 1 and k}

        print(f"Total unique case numbers: {len(set(case_numbers))}")
        print(f"Duplicate case numbers: {len(duplicates)}")
        if duplicates:
            print("Duplicate cases:")
            for case_num, count in list(duplicates.items())[:5]:
                print(f"  - {case_num}: {count} occurrences")

        # Quality assessment
        print("\n" + "=" * 40)
        print("DATA QUALITY ASSESSMENT")
        print("=" * 40)

        low_quality = 0
        medium_quality = 0
        high_quality = 0

        for item in data:
            # Quality scoring based on content completeness
            score = 0
            for field in key_fields:
                content = str(item.get(field, '')).strip()
                if content and len(content) > 50:
                    score += 1
                elif content and len(content) > 10:
                    score += 0.5

            if score < 1:
                low_quality += 1
            elif score < 2:
                medium_quality += 1
            else:
                high_quality += 1

        print(f"High quality entries (score >= 2): {high_quality}")
        print(f"Medium quality entries (1 <= score < 2): {medium_quality}")
        print(f"Low quality entries (score < 1): {low_quality}")

        # Cleaning recommendations
        print("\n" + "=" * 40)
        print("CLEANING RECOMMENDATIONS")
        print("=" * 40)

        entries_to_remove = 0

        # Entries with all key fields empty
        all_empty = 0
        for item in data:
            if all(not str(item.get(field, '')).strip() for field in key_fields):
                all_empty += 1

        # Entries with very minimal content
        minimal_content = 0
        for item in data:
            total_content = sum(len(str(item.get(field, '')).strip()) for field in key_fields)
            if total_content < 20:  # Less than 20 characters total
                minimal_content += 1

        print(f"Entries with all key fields empty: {all_empty}")
        print(f"Entries with minimal content (<20 chars): {minimal_content}")
        print(f"Recommended for removal: {max(all_empty, minimal_content)} entries")
        print(f"Estimated clean dataset size: {total_entries - max(all_empty, minimal_content)}")

        return {
            'total_entries': total_entries,
            'field_stats': field_stats,
            'content_stats': content_stats,
            'latest_date': latest_date if dates else None,
            'earliest_date': earliest_date if dates else None,
            'duplicates': len(duplicates),
            'quality_scores': {
                'high': high_quality,
                'medium': medium_quality,
                'low': low_quality
            },
            'cleaning_candidates': {
                'all_empty': all_empty,
                'minimal_content': minimal_content
            }
        }

    def analyze_law_center_data(self):
        """Analyze data_moleg.json file"""
        print("\n" + "=" * 60)
        print("ANALYZING data_moleg.json")
        print("=" * 60)

        with open(self.moleg_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_entries = len(data)
        print(f"Total entries: {total_entries}")

        # Analyze data structure
        if data and isinstance(data[0], dict):
            keys = list(data[0].keys())
            print(f"\nData structure keys: {keys}")

        # Field analysis
        field_stats = {}
        for key in keys:
            filled = sum(1 for item in data if item.get(key) and str(item.get(key)).strip())
            empty = total_entries - filled
            field_stats[key] = {
                'filled': filled,
                'empty': empty,
                'fill_rate': (filled / total_entries) * 100
            }

        print("\n" + "=" * 40)
        print("FIELD COMPLETION ANALYSIS")
        print("=" * 40)
        for field, stats in field_stats.items():
            print(f"{field}:")
            print(f"  - Filled: {stats['filled']} ({stats['fill_rate']:.1f}%)")
            print(f"  - Empty: {stats['empty']} ({100-stats['fill_rate']:.1f}%)")

        # Content analysis
        print("\n" + "=" * 40)
        print("CONTENT ANALYSIS")
        print("=" * 40)

        content_field = '내용'
        content_lengths = []

        for item in data:
            content = str(item.get(content_field, '')).strip()
            content_lengths.append(len(content))

        if content_lengths:
            avg_length = sum(content_lengths) / len(content_lengths)
            max_length = max(content_lengths)
            min_length = min(content_lengths)

            print(f"Content field ('{content_field}'):")
            print(f"  - Average length: {avg_length:.1f}")
            print(f"  - Max length: {max_length}")
            print(f"  - Min length: {min_length}")

            # Length distribution
            very_long = sum(1 for l in content_lengths if l > 5000)
            long = sum(1 for l in content_lengths if 2000 < l <= 5000)
            medium = sum(1 for l in content_lengths if 500 < l <= 2000)
            short = sum(1 for l in content_lengths if 50 < l <= 500)
            very_short = sum(1 for l in content_lengths if 0 < l <= 50)
            empty = sum(1 for l in content_lengths if l == 0)

            print(f"\nLength distribution:")
            print(f"  - Very long (>5000): {very_long}")
            print(f"  - Long (2000-5000): {long}")
            print(f"  - Medium (500-2000): {medium}")
            print(f"  - Short (50-500): {short}")
            print(f"  - Very short (0-50): {very_short}")
            print(f"  - Empty: {empty}")

        # Analyze 판례번호 patterns
        print("\n" + "=" * 40)
        print("판례번호 PATTERN ANALYSIS")
        print("=" * 40)

        case_numbers = [item.get('판례번호', '') for item in data if item.get('판례번호')]
        case_patterns = defaultdict(int)

        for case_num in case_numbers:
            # Extract pattern (court type, year, etc.)
            if '대법원' in case_num:
                case_patterns['대법원'] += 1
            elif '고등법원' in case_num or '고법' in case_num:
                case_patterns['고등법원'] += 1
            elif '지방법원' in case_num or '지법' in case_num:
                case_patterns['지방법원'] += 1
            else:
                case_patterns['기타'] += 1

        print("Court type distribution:")
        for pattern, count in case_patterns.items():
            print(f"  - {pattern}: {count}")

        # Date extraction from content
        print("\n" + "=" * 40)
        print("DATE EXTRACTION ANALYSIS")
        print("=" * 40)

        dates_found = []
        date_patterns = [
            r'\d{4}\. \d{1,2}\. \d{1,2}\.',  # 2024. 1. 1.
            r'\d{4}-\d{2}-\d{2}',            # 2024-01-01
            r'\d{4}\년 \d{1,2}\월 \d{1,2}\일'  # 2024년 1월 1일
        ]

        for item in data:
            content = str(item.get('내용', ''))
            case_num = str(item.get('판례번호', ''))

            # Try to extract date from case number first
            year_match = re.search(r'(\d{4})', case_num)
            if year_match:
                year = int(year_match.group(1))
                if 2000 <= year <= 2025:
                    dates_found.append(year)

            # Try to extract dates from content
            for pattern in date_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    try:
                        if '.' in match:
                            date_obj = datetime.strptime(match.replace(' ', ''), '%Y.%m.%d.')
                        elif '-' in match:
                            date_obj = datetime.strptime(match, '%Y-%m-%d')
                        elif '년' in match:
                            date_str = match.replace('년', '').replace('월', '').replace('일', '')
                            # This would need more complex parsing
                            continue

                        if date_obj.year >= 2000:
                            dates_found.append(date_obj.year)
                    except:
                        continue

        if dates_found:
            year_dist = Counter(dates_found)
            print(f"Dates found in content: {len(dates_found)}")
            print(f"Year distribution (top 10):")
            for year, count in year_dist.most_common(10):
                print(f"  - {year}: {count}")

            latest_year = max(dates_found)
            print(f"Latest year found: {latest_year}")

        # Structure refinement recommendations
        print("\n" + "=" * 40)
        print("STRUCTURE REFINEMENT RECOMMENDATIONS")
        print("=" * 40)

        print("Potential new fields to extract from '내용':")
        print("1. 선고일자 (Decision date)")
        print("2. 법원명 (Court name)")
        print("3. 사건유형 (Case type)")
        print("4. 판결요지 (Decision summary)")
        print("5. 참조조문 (Referenced articles)")
        print("6. 판결결과 (Decision result)")

        return {
            'total_entries': total_entries,
            'field_stats': field_stats,
            'content_stats': {
                'avg_length': avg_length if content_lengths else 0,
                'max_length': max_length if content_lengths else 0,
                'distribution': {
                    'very_long': very_long if content_lengths else 0,
                    'long': long if content_lengths else 0,
                    'medium': medium if content_lengths else 0,
                    'short': short if content_lengths else 0,
                    'very_short': very_short if content_lengths else 0,
                    'empty': empty if content_lengths else 0
                }
            },
            'case_patterns': dict(case_patterns),
            'latest_year': max(dates_found) if dates_found else None,
            'dates_found': len(dates_found)
        }

    def run_full_analysis(self):
        """Run complete analysis of both files"""
        print("LEGAL PRECEDENTS DATA ANALYSIS")
        print("Starting comprehensive data analysis...")

        court_analysis = self.analyze_court_cases()
        law_center_analysis = self.analyze_law_center_data()

        # Generate summary report
        print("\n" + "=" * 60)
        print("SUMMARY REPORT")
        print("=" * 60)

        total_entries = court_analysis['total_entries'] + law_center_analysis['total_entries']
        print(f"Total entries across both files: {total_entries}")
        print(f"  - data_kcs.json: {court_analysis['total_entries']}")
        print(f"  - data_moleg.json: {law_center_analysis['total_entries']}")

        if court_analysis['latest_date']:
            print(f"\nLatest date in court cases: {court_analysis['latest_date'].strftime('%Y-%m-%d')}")
        if law_center_analysis['latest_year']:
            print(f"Latest year in law center data: {law_center_analysis['latest_year']}")

        print(f"\nData quality overview:")
        print(f"  - Court cases needing cleaning: {court_analysis['cleaning_candidates']['minimal_content']}")
        print(f"  - Duplicates in court cases: {court_analysis['duplicates']}")

        return {
            'court_cases': court_analysis,
            'law_center': law_center_analysis,
            'summary': {
                'total_entries': total_entries,
                'latest_court_date': court_analysis['latest_date'],
                'latest_law_year': law_center_analysis['latest_year']
            }
        }

if __name__ == "__main__":
    analyzer = LegalDataAnalyzer()
    results = analyzer.run_full_analysis()