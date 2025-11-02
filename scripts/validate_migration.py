"""
Migration validation script for JobSearchAI database.

Verifies that all JSON data was migrated successfully to SQLite.
"""

import json
import glob
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.db_utils import JobMatchDatabase


def validate_migration(
    json_dir="job_matches",
    db_path="instance/jobsearchai.db",
    sample_size=10
):
    """
    Validate that JSON data was migrated correctly to database
    
    Args:
        json_dir: Directory containing JSON files
        db_path: Path to SQLite database
        sample_size: Number of random records to sample-check
        
    Returns:
        True if validation passes, False otherwise
    """
    print("\n" + "="*60)
    print("Migration Validation Tool")
    print("="*60 + "\n")
    
    validation_passed = True
    issues = []
    
    # Connect to database
    db = JobMatchDatabase(db_path)
    db.connect()
    
    if not db.conn:
        print("❌ Failed to connect to database")
        return False
    
    # Count database records
    print("📊 Counting database records...")
    cursor = db.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM job_matches")
    db_count = cursor.fetchone()[0]
    print(f"   Database: {db_count} job matches")
    
    # Count JSON records
    print("\n📊 Counting JSON records...")
    json_pattern = f"{json_dir}/job_matches_*.json"
    json_files = sorted(glob.glob(json_pattern))
    
    if not json_files:
        print(f"⚠️  No JSON files found matching pattern: {json_pattern}")
        print("   Cannot validate migration without source files")
        db.close()
        return True  # Not necessarily a failure
    
    json_count = 0
    file_counts = {}
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                matches = json.load(f)
                count = len(matches)
                json_count += count
                file_counts[json_file] = count
        except Exception as e:
            print(f"⚠️  Error reading {json_file}: {e}")
            issues.append(f"Failed to read JSON file: {json_file}")
    
    print(f"   JSON files: {json_count} job matches across {len(json_files)} files")
    
    # Compare counts
    print(f"\n📈 Count Comparison:")
    print(f"   JSON:     {json_count}")
    print(f"   Database: {db_count}")
    print(f"   Difference: {abs(json_count - db_count)}")
    
    if db_count == 0:
        print("\n❌ VALIDATION FAILED: No records in database")
        issues.append("Database is empty")
        validation_passed = False
    elif json_count > db_count:
        difference = json_count - db_count
        print(f"\n⚠️  WARNING: {difference} fewer records in database than JSON")
        print("   This is expected if there were duplicates or errors during migration")
        issues.append(f"Missing {difference} records (may be intentional)")
    elif db_count > json_count:
        difference = db_count - json_count
        print(f"\n⚠️  WARNING: {difference} more records in database than JSON")
        print("   Database may contain records from other sources")
        issues.append(f"Extra {difference} records in database")
    else:
        print("\n✅ Record counts match exactly")
    
    # Verify schema
    print(f"\n📋 Verifying database schema...")
    
    required_columns = [
        'id', 'job_url', 'search_term', 'cv_key', 'job_title', 'company_name',
        'location', 'overall_match', 'reasoning', 'scraped_data', 'matched_at'
    ]
    
    cursor.execute("PRAGMA table_info(job_matches)")
    columns = [row[1] for row in cursor.fetchall()]
    
    missing_columns = [col for col in required_columns if col not in columns]
    
    if missing_columns:
        print(f"❌ Missing required columns: {', '.join(missing_columns)}")
        issues.append(f"Missing columns: {missing_columns}")
        validation_passed = False
    else:
        print(f"✅ All required columns present ({len(columns)} total)")
    
    # Verify indexes
    print(f"\n🔍 Verifying indexes...")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='job_matches'")
    indexes = [row[0] for row in cursor.fetchall()]
    
    required_indexes = [
        'idx_job_matches_search_term',
        'idx_job_matches_cv_key',
        'idx_job_matches_overall_match'
    ]
    
    missing_indexes = [idx for idx in required_indexes if idx not in indexes]
    
    if missing_indexes:
        print(f"⚠️  Missing recommended indexes: {', '.join(missing_indexes)}")
        issues.append(f"Missing indexes: {missing_indexes}")
    else:
        print(f"✅ Key indexes present ({len(indexes)} total)")
    
    # Sample data integrity check
    if db_count > 0 and sample_size > 0:
        print(f"\n🔬 Sample checking {min(sample_size, db_count)} random records...")
        
        cursor.execute(f"""
            SELECT job_url, job_title, company_name, overall_match, scraped_data
            FROM job_matches
            ORDER BY RANDOM()
            LIMIT {sample_size}
        """)
        
        samples = cursor.fetchall()
        integrity_issues = 0
        
        for i, (job_url, job_title, company_name, overall_match, scraped_data) in enumerate(samples, 1):
            # Check required fields are not null
            if not job_url:
                print(f"  [{i}] ❌ NULL job_url")
                integrity_issues += 1
            
            # Check overall_match is valid range
            if overall_match is not None and (overall_match < 0 or overall_match > 10):
                print(f"  [{i}] ⚠️  Invalid overall_match: {overall_match}")
                integrity_issues += 1
            
            # Check scraped_data is valid JSON
            if scraped_data:
                try:
                    json.loads(scraped_data)
                except json.JSONDecodeError:
                    print(f"  [{i}] ❌ Invalid JSON in scraped_data")
                    integrity_issues += 1
        
        if integrity_issues == 0:
            print(f"✅ All {len(samples)} sampled records have valid data")
        else:
            print(f"❌ Found {integrity_issues} integrity issues in sample")
            issues.append(f"Data integrity issues: {integrity_issues}")
            validation_passed = False
    
    # Check for unique constraint violations
    print(f"\n🔍 Checking for potential duplicates...")
    cursor.execute("""
        SELECT job_url, search_term, cv_key, COUNT(*) as count
        FROM job_matches
        GROUP BY job_url, search_term, cv_key
        HAVING count > 1
    """)
    
    duplicates = cursor.fetchall()
    
    if duplicates:
        print(f"⚠️  Found {len(duplicates)} duplicate combinations:")
        for job_url, search_term, cv_key, count in duplicates[:5]:  # Show first 5
            print(f"  - {job_url[:50]}... ({count} times)")
        if len(duplicates) > 5:
            print(f"  ... and {len(duplicates) - 5} more")
        issues.append(f"Duplicate records: {len(duplicates)}")
        validation_passed = False
    else:
        print(f"✅ No duplicates found (composite key enforced)")
    
    # Performance check
    print(f"\n⏱️  Performance check...")
    import time
    
    # Query performance test
    test_queries = [
        ("SELECT * FROM job_matches WHERE search_term = ? LIMIT 10", ["test"]),
        ("SELECT * FROM job_matches WHERE cv_key = ? LIMIT 10", ["test"]),
        ("SELECT * FROM job_matches WHERE overall_match >= ? LIMIT 10", [7]),
    ]
    
    slow_queries = 0
    for query, params in test_queries:
        start = time.time()
        cursor.execute(query, params)
        cursor.fetchall()
        elapsed = (time.time() - start) * 1000  # Convert to ms
        
        if elapsed > 100:  # Threshold: 100ms
            print(f"  ⚠️  Slow query: {elapsed:.2f}ms")
            slow_queries += 1
    
    if slow_queries == 0:
        print(f"✅ All test queries completed in <100ms")
    else:
        print(f"⚠️  {slow_queries} queries exceeded 100ms threshold")
        issues.append(f"Slow queries: {slow_queries}")
    
    db.close()
    
    # Generate report
    print(f"\n{'='*60}")
    print("Validation Report")
    print(f"{'='*60}")
    
    if validation_passed and len(issues) == 0:
        print("✅ VALIDATION PASSED")
        print("   All checks successful, migration is valid")
        print(f"{'='*60}\n")
        return True
    elif validation_passed and len(issues) > 0:
        print("⚠️  VALIDATION PASSED WITH WARNINGS")
        print(f"   {len(issues)} non-critical issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print(f"{'='*60}\n")
        return True
    else:
        print("❌ VALIDATION FAILED")
        print(f"   {len(issues)} issues found:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n   Please review and fix issues before proceeding")
        print(f"{'='*60}\n")
        return False


def generate_migration_report(
    json_dir="job_matches",
    db_path="instance/jobsearchai.db",
    output_file="migration_report.txt"
):
    """
    Generate detailed migration report
    
    Args:
        json_dir: Directory containing JSON files
        db_path: Path to SQLite database
        output_file: Path to output report file
    """
    report_lines = []
    report_lines.append("="*60)
    report_lines.append("Migration Report")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("="*60)
    report_lines.append("")
    
    # Database info
    db = JobMatchDatabase(db_path)
    db.connect()
    
    if db.conn:
        cursor = db.conn.cursor()
        
        # Total records
        cursor.execute("SELECT COUNT(*) FROM job_matches")
        total = cursor.fetchone()[0]
        report_lines.append(f"Total Records: {total}")
        
        # By search term
        cursor.execute("""
            SELECT search_term, COUNT(*) as count
            FROM job_matches
            GROUP BY search_term
            ORDER BY count DESC
        """)
        report_lines.append("\nRecords by Search Term:")
        for term, count in cursor.fetchall():
            report_lines.append(f"  {term}: {count}")
        
        # By CV key
        cursor.execute("""
            SELECT cv_key, COUNT(*) as count
            FROM job_matches
            GROUP BY cv_key
            ORDER BY count DESC
        """)
        report_lines.append("\nRecords by CV Key:")
        for key, count in cursor.fetchall():
            report_lines.append(f"  {key}: {count}")
        
        # Score distribution
        cursor.execute("""
            SELECT overall_match, COUNT(*) as count
            FROM job_matches
            GROUP BY overall_match
            ORDER BY overall_match DESC
        """)
        report_lines.append("\nScore Distribution:")
        for score, count in cursor.fetchall():
            report_lines.append(f"  Score {score}: {count}")
        
        db.close()
    
    report_lines.append("")
    report_lines.append("="*60)
    
    # Write report
    report_text = "\n".join(report_lines)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report_text)
    
    print(f"📄 Report saved to: {output_file}")
    print(report_text)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Validate migration from JSON to SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run validation
  python scripts/validate_migration.py
  
  # Generate detailed report
  python scripts/validate_migration.py --report
  
  # Custom sample size
  python scripts/validate_migration.py --sample-size 20
        """
    )
    
    parser.add_argument(
        '--json-dir',
        default='job_matches',
        help='Directory containing JSON files (default: job_matches)'
    )
    
    parser.add_argument(
        '--db-path',
        default='instance/jobsearchai.db',
        help='Path to SQLite database (default: instance/jobsearchai.db)'
    )
    
    parser.add_argument(
        '--sample-size',
        type=int,
        default=10,
        help='Number of records to sample-check (default: 10)'
    )
    
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed migration report'
    )
    
    parser.add_argument(
        '--output',
        default='migration_report.txt',
        help='Output file for report (default: migration_report.txt)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.report:
            generate_migration_report(
                args.json_dir,
                args.db_path,
                args.output
            )
            sys.exit(0)
        else:
            success = validate_migration(
                args.json_dir,
                args.db_path,
                args.sample_size
            )
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
