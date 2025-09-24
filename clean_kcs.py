#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KCS Data Cleaner
Conservative cleaning approach for data_kcs.json only
"""

import json
import re
from datetime import datetime
import os
import shutil

class KCSDataCleaner:
    def __init__(self):
        self.kcs_data_file = "data_kcs.json"
        self.backup_suffix = f"_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def create_backup(self, filename):
        """Create backup of original file"""
        backup_name = f"{filename}{self.backup_suffix}"
        shutil.copy2(filename, backup_name)
        print(f"✓ Backup created: {backup_name}")
        return backup_name

    def clean_kcs_data(self, dry_run=True):
        """
        Clean data_kcs.json using conservative approach
        Conservative Criteria:
        1. Remove entries with total content < 20 characters in key fields
        2. Remove exact duplicates (keep first occurrence)
        """
        print("=" * 60)
        print("CLEANING data_kcs.json (Conservative Approach)")
        print("=" * 60)

        # Load data
        with open(self.kcs_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original_count = len(data)
        print(f"Original entries: {original_count}")

        # Track removed entries for reporting
        removed_entries = {
            'minimal_content': [],
            'duplicates': []
        }

        cleaned_data = []
        seen_case_numbers = set()

        key_fields = ['판결주문', '청구취지', '판결이유']

        print(f"\nApplying cleaning criteria:")
        print(f"1. Remove entries with < 20 total characters in key fields")
        print(f"2. Remove exact duplicates (keep first occurrence)")

        for i, entry in enumerate(data):
            case_number = entry.get('사건번호', '').strip()

            # Criteria 1: Check for minimal content (< 20 total characters)
            total_content_length = 0
            for field in key_fields:
                content = str(entry.get(field, '')).strip()
                total_content_length += len(content)

            if total_content_length < 20:
                removed_entries['minimal_content'].append({
                    'index': i,
                    'case_number': case_number,
                    'date': entry.get('선고일자\n(종결일자)', ''),
                    'total_chars': total_content_length,
                    'details': {
                        '판결주문': len(str(entry.get('판결주문', '')).strip()),
                        '청구취지': len(str(entry.get('청구취지', '')).strip()),
                        '판결이유': len(str(entry.get('판결이유', '')).strip())
                    }
                })
                continue

            # Criteria 2: Check for duplicates (keep first occurrence)
            if case_number and case_number in seen_case_numbers:
                removed_entries['duplicates'].append({
                    'index': i,
                    'case_number': case_number,
                    'date': entry.get('선고일자\n(종결일자)', '')
                })
                continue

            # Add to cleaned data
            cleaned_data.append(entry)
            if case_number:
                seen_case_numbers.add(case_number)

        cleaned_count = len(cleaned_data)
        removed_count = original_count - cleaned_count

        # Report cleaning results
        print(f"\n" + "=" * 40)
        print("CLEANING RESULTS")
        print("=" * 40)
        print(f"├─ Removed for minimal content: {len(removed_entries['minimal_content'])}")
        print(f"├─ Removed duplicates: {len(removed_entries['duplicates'])}")
        print(f"├─ Total removed: {removed_count}")
        print(f"├─ Final count: {cleaned_count}")
        print(f"└─ Retention rate: {(cleaned_count/original_count)*100:.1f}%")

        # Show examples of removed entries
        if removed_entries['minimal_content']:
            print(f"\n" + "=" * 40)
            print("EXAMPLES OF MINIMAL CONTENT ENTRIES REMOVED")
            print("=" * 40)
            for i, item in enumerate(removed_entries['minimal_content'][:5]):
                print(f"{i+1}. Case: {item['case_number']}")
                print(f"   Date: {item['date']}")
                print(f"   Total chars: {item['total_chars']}")
                print(f"   Field lengths: 판결주문={item['details']['판결주문']}, 청구취지={item['details']['청구취지']}, 판결이유={item['details']['판결이유']}")
                print()

        if removed_entries['duplicates']:
            print(f"DUPLICATE ENTRIES REMOVED:")
            for item in removed_entries['duplicates']:
                print(f"  - Case: {item['case_number']} (Date: {item['date']})")

        # Validate cleaned data
        print(f"\n" + "=" * 40)
        print("DATA VALIDATION")
        print("=" * 40)

        # Check cleaned data quality
        high_quality = 0
        medium_quality = 0
        low_quality = 0

        for entry in cleaned_data:
            score = 0
            for field in key_fields:
                content = str(entry.get(field, '')).strip()
                if content and len(content) > 50:
                    score += 1
                elif content and len(content) > 10:
                    score += 0.5

            if score >= 2:
                high_quality += 1
            elif score >= 1:
                medium_quality += 1
            else:
                low_quality += 1

        print(f"Quality distribution in cleaned data:")
        print(f"├─ High quality (score >= 2): {high_quality} ({(high_quality/cleaned_count)*100:.1f}%)")
        print(f"├─ Medium quality (1 <= score < 2): {medium_quality} ({(medium_quality/cleaned_count)*100:.1f}%)")
        print(f"└─ Low quality (score < 1): {low_quality} ({(low_quality/cleaned_count)*100:.1f}%)")

        # Save cleaned data
        if not dry_run:
            # Create backup first
            self.create_backup(self.kcs_data_file)

            # Save cleaned data
            cleaned_filename = self.kcs_data_file.replace('.json', '_cleaned.json')
            with open(cleaned_filename, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            print(f"\n✓ Cleaned data saved to: {cleaned_filename}")

            # Generate detailed cleaning report
            report = {
                'cleaning_summary': {
                    'original_count': original_count,
                    'cleaned_count': cleaned_count,
                    'removed_count': removed_count,
                    'retention_rate': round((cleaned_count/original_count)*100, 2)
                },
                'removal_details': {
                    'minimal_content_entries': len(removed_entries['minimal_content']),
                    'duplicate_entries': len(removed_entries['duplicates'])
                },
                'cleaning_criteria': [
                    'Total content in key fields (판결주문, 청구취지, 판결이유) < 20 characters',
                    'Exact duplicate case numbers (kept first occurrence)'
                ],
                'quality_distribution': {
                    'high_quality': high_quality,
                    'medium_quality': medium_quality,
                    'low_quality': low_quality
                },
                'removed_entries_details': {
                    'minimal_content': removed_entries['minimal_content'],
                    'duplicates': removed_entries['duplicates']
                },
                'timestamp': datetime.now().isoformat(),
                'backup_file': f"{self.kcs_data_file}{self.backup_suffix}"
            }

            with open('kcs_cleaning_report.json', 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print("✓ Detailed cleaning report saved to: kcs_cleaning_report.json")

        else:
            print(f"\n[DRY RUN] Would clean {removed_count} entries")
            print(f"[DRY RUN] To apply changes, run with dry_run=False")

        return {
            'original_count': original_count,
            'cleaned_count': cleaned_count,
            'removed_entries': removed_entries,
            'cleaned_data': cleaned_data if not dry_run else None
        }

    def get_latest_date(self):
        """Get latest date from KCS data for update baseline"""
        with open(self.kcs_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        dates = []
        date_field = '선고일자\n(종결일자)'

        for entry in data:
            date_str = str(entry.get(date_field, '')).strip()
            if date_str and re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    dates.append(date_obj)
                except:
                    continue

        latest_date = max(dates) if dates else None

        print(f"\n" + "=" * 40)
        print("BASELINE DATE INFORMATION")
        print("=" * 40)
        print(f"Latest date in KCS data: {latest_date.strftime('%Y-%m-%d') if latest_date else 'None'}")
        print(f"Total valid dates: {len(dates)}")
        if dates:
            print(f"Date range: {min(dates).strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")

        return latest_date

if __name__ == "__main__":
    cleaner = KCSDataCleaner()

    print("KCS DATA CLEANING TOOL")
    print("Conservative approach approved for data_kcs.json")
    print()

    # Run dry run first
    print("Running DRY RUN to preview changes...")
    results = cleaner.clean_kcs_data(dry_run=True)

    # Get baseline date
    latest_date = cleaner.get_latest_date()

    print(f"\n" + "=" * 60)
    print("READY TO APPLY CLEANING")
    print("=" * 60)
    print("To apply the cleaning changes, uncomment and run:")
    print("# results = cleaner.clean_kcs_data(dry_run=False)")