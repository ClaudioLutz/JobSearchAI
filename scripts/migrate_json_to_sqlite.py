"""
Migration script to move legacy JSON match files to SQLite database.

This script:
1. Discovers all JSON files in job_matches/ directory
2. Prompts user for metadata (search_term, cv_key)
3. Migrates match data to database with proper structure
4. Handles duplicates gracefully (skip or update)
5. Logs migration progress and statistics
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
from utils.cv_utils import generate_cv_key
from utils.url_utils import URLNormalizer


def migrate_legacy_json_files(
    json_dir="job_matches",
    db_path="instance/jobsearchai.db",
    dry_run=False,
    force=False
):
    """
    Migrate existing JSON match files to SQLite database
    
    Interactive migration with user prompts for missing data
    
    Args:
        json_dir: Directory containing JSON files
        db_path: Path to SQLite database
        dry_run: If True, preview migration without making changes
        force: If True, overwrite duplicates instead of skipping
    """
    print("\n" + "="*60)
    print("Legacy JSON to SQLite Migration Tool")
    print("="*60 + "\n")
    
    # Initialize database
    db = JobMatchDatabase(db_path)
    db.connect()
    db.init_database()
    
    # Initialize URL normalizer
    normalizer = URLNormalizer()
    
    # Find JSON files
    json_pattern = f"{json_dir}/job_matches_*.json"
    json_files = sorted(glob.glob(json_pattern))
    
    if not json_files:
        print(f"❌ No JSON files found matching pattern: {json_pattern}")
        db.close()
        return
    
    print(f"📁 Found {len(json_files)} JSON files to migrate\n")
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    
    # Statistics
    total_migrated = 0
    total_duplicates = 0
    total_errors = 0
    total_skipped_files = 0
    
    # Process each file
    for file_idx, json_file in enumerate(json_files, 1):
        print(f"\n{'='*60}")
        print(f"File {file_idx}/{len(json_files)}: {json_file}")
        print(f"{'='*60}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                matches = json.load(f)
        except Exception as e:
            print(f"❌ Error reading file: {e}")
            total_errors += 1
            continue
        
        print(f"📊 File contains {len(matches)} job matches")
        
        # Prompt for metadata
        print("\n📝 Please provide metadata for this batch:")
        search_term = input("  Search term (e.g., 'Python Developer', 'Data Scientist'): ").strip()
        
        if not search_term:
            print("⚠️  Skipping file - no search term provided")
            total_skipped_files += 1
            continue
        
        # Try to extract CV path from first match
        default_cv_path = None
        if matches and 'cv_path' in matches[0]:
            default_cv_path = matches[0]['cv_path']
            # Convert relative path to absolute if needed
            if not default_cv_path.startswith('process_cv/'):
                default_cv_path = f"process_cv/cv-data/{default_cv_path}"
        
        if default_cv_path:
            cv_path_input = input(f"  CV path (press Enter for '{default_cv_path}'): ").strip()
            cv_path = cv_path_input if cv_path_input else default_cv_path
        else:
            cv_path = input("  CV path (e.g., 'process_cv/cv-data/input/Lebenslauf.pdf'): ").strip()
        
        if not cv_path:
            print("⚠️  Skipping file - no CV path provided")
            total_skipped_files += 1
            continue
        
        # Generate CV key
        try:
            if os.path.exists(cv_path):
                cv_key = generate_cv_key(cv_path)
                print(f"  ✓ Generated CV key: {cv_key}")
            else:
                print(f"  ⚠️  CV file not found: {cv_path}")
                cv_key = input("  Enter CV key manually (16 hex chars, or press Enter to skip): ").strip()
                if not cv_key or len(cv_key) != 16:
                    print("  ⚠️  Invalid CV key, skipping file")
                    total_skipped_files += 1
                    continue
        except Exception as e:
            print(f"  ❌ Error generating CV key: {e}")
            total_errors += 1
            continue
        
        if dry_run:
            print(f"\n[DRY RUN] Would migrate {len(matches)} matches with:")
            print(f"  - Search term: {search_term}")
            print(f"  - CV key: {cv_key}")
            continue
        
        # Migrate each match
        print(f"\n🔄 Migrating {len(matches)} matches...")
        file_migrated = 0
        file_duplicates = 0
        file_errors = 0
        
        for i, match in enumerate(matches, 1):
            try:
                # Normalize URL
                raw_url = match.get('application_url') or match.get('Application URL', '')
                if not raw_url:
                    print(f"  [{i}/{len(matches)}] ⚠️  Skipping - no URL")
                    file_errors += 1
                    continue
                
                job_url = normalizer.normalize(raw_url)
                
                # Check if already exists
                if not force and db.job_exists(job_url, search_term, cv_key):
                    file_duplicates += 1
                    print(f"  [{i}/{len(matches)}] ⊘ Duplicate: {match.get('job_title', 'Unknown')[:50]}")
                    continue
                
                # Prepare match data
                match_data = {
                    'job_url': job_url,
                    'search_term': search_term,
                    'cv_key': cv_key,
                    'job_title': match.get('job_title', ''),
                    'company_name': match.get('company_name', ''),
                    'location': match.get('location', ''),
                    'posting_date': match.get('posting_date'),
                    'salary_range': match.get('salary_range'),
                    'overall_match': match.get('overall_match', 0),
                    'skills_match': match.get('skills_match'),
                    'experience_match': match.get('experience_match'),
                    'education_fit': match.get('education_fit'),
                    'career_trajectory_alignment': match.get('career_trajectory_alignment'),
                    'preference_match': match.get('preference_match'),
                    'potential_satisfaction': match.get('potential_satisfaction'),
                    'location_compatibility': match.get('location_compatibility'),
                    'reasoning': match.get('reasoning', ''),
                    'scraped_data': json.dumps(match),  # Store complete match as JSON string
                    'scraped_at': datetime.now().isoformat()
                }
                
                # Insert into database
                if force:
                    # Update existing or insert new
                    with db.transaction():
                        if db.conn:
                            cursor = db.conn.cursor()
                            cursor.execute("""
                                INSERT OR REPLACE INTO job_matches 
                                (job_url, search_term, cv_key, job_title, company_name, location,
                                 posting_date, salary_range, overall_match, skills_match, experience_match,
                                 education_fit, career_trajectory_alignment, preference_match,
                                 potential_satisfaction, location_compatibility, reasoning,
                                 scraped_data, scraped_at, matched_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """, (
                                match_data['job_url'], match_data['search_term'], match_data['cv_key'],
                                match_data['job_title'], match_data['company_name'], match_data['location'],
                                match_data['posting_date'], match_data['salary_range'], match_data['overall_match'],
                                match_data['skills_match'], match_data['experience_match'],
                                match_data['education_fit'], match_data['career_trajectory_alignment'],
                                match_data['preference_match'], match_data['potential_satisfaction'],
                                match_data['location_compatibility'], match_data['reasoning'],
                                match_data['scraped_data'], match_data['scraped_at']
                            ))
                    file_migrated += 1
                    print(f"  [{i}/{len(matches)}] ✓ {match_data['job_title'][:50]}")
                else:
                    row_id = db.insert_job_match(match_data)
                    
                    if row_id:
                        file_migrated += 1
                        print(f"  [{i}/{len(matches)}] ✓ {match_data['job_title'][:50]}")
                    else:
                        file_duplicates += 1
                        print(f"  [{i}/{len(matches)}] ⊘ Duplicate")
                        
            except Exception as e:
                file_errors += 1
                print(f"  [{i}/{len(matches)}] ✗ Error: {str(e)}")
        
        # File summary
        print(f"\n📈 File Results:")
        print(f"  ✓ Migrated:   {file_migrated}")
        print(f"  ⊘ Duplicates: {file_duplicates}")
        print(f"  ✗ Errors:     {file_errors}")
        
        total_migrated += file_migrated
        total_duplicates += file_duplicates
        total_errors += file_errors
    
    db.close()
    
    # Final summary
    print(f"\n{'='*60}")
    print("Migration Complete")
    print(f"{'='*60}")
    print(f"📁 Files processed:  {len(json_files)}")
    print(f"   Files skipped:    {total_skipped_files}")
    print(f"✓  Total migrated:   {total_migrated}")
    print(f"⊘  Total duplicates: {total_duplicates}")
    print(f"✗  Total errors:     {total_errors}")
    print(f"{'='*60}\n")
    
    if not dry_run and total_migrated > 0:
        print("✅ Migration successful!")
        print("💡 Tip: Run validation script to verify: python scripts/validate_migration.py")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Migrate legacy JSON match files to SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview migration without making changes
  python scripts/migrate_json_to_sqlite.py --dry-run
  
  # Run migration interactively
  python scripts/migrate_json_to_sqlite.py
  
  # Force overwrite existing records
  python scripts/migrate_json_to_sqlite.py --force
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making changes'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Overwrite existing records instead of skipping duplicates'
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
    
    args = parser.parse_args()
    
    try:
        migrate_legacy_json_files(
            json_dir=args.json_dir,
            db_path=args.db_path,
            dry_run=args.dry_run,
            force=args.force
        )
    except KeyboardInterrupt:
        print("\n\n⚠️  Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
