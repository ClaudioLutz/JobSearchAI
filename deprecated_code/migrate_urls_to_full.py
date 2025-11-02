#!/usr/bin/env python3
"""
Data Migration Script: Convert Relative URLs to Full URLs in Job Matches
Story 1.4: Application Queue Integration Bridge

This script migrates existing job match files to use full URLs instead of relative paths.
It processes all job_matches_*.json files in the job_matches directory.

Usage:
    python migrate_urls_to_full.py [--dry-run] [--backup-dir BACKUP_DIR]

Arguments:
    --dry-run: Preview changes without modifying files
    --backup-dir: Directory for backups (default: job_matches/backups)
"""

import json
import shutil
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.url_utils import URLNormalizer


def migrate_match_file(file_path: Path, dry_run: bool = False, backup_dir: Path = None) -> dict:
    """
    Migrate a single match file to use full URLs.
    
    Args:
        file_path: Path to the match JSON file
        dry_run: If True, preview changes without modifying files
        backup_dir: Directory to store backups
        
    Returns:
        Dictionary with migration results
    """
    result = {
        'file': file_path.name,
        'migrated': False,
        'already_migrated': False,
        'matches_updated': 0,
        'errors': []
    }
    
    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        if not isinstance(matches, list):
            result['errors'].append("File does not contain a list of matches")
            return result
        
        # Check if already migrated
        if matches and matches[0].get('url_migrated'):
            result['already_migrated'] = True
            return result
        
        # Initialize URLNormalizer
        normalizer = URLNormalizer()
        modified = False
        
        # Process each match
        for match in matches:
            application_url = match.get('application_url', '')
            
            # Skip if no URL or already full URL
            if not application_url or application_url.startswith('http'):
                continue
            
            # Convert to full URL
            full_url = normalizer.to_full_url(application_url)
            
            if full_url != application_url:
                match['application_url'] = full_url
                result['matches_updated'] += 1
                modified = True
        
        # Add migration flag
        if modified:
            for match in matches:
                match['url_migrated'] = True
            
            if not dry_run:
                # Create backup if backup_dir specified
                if backup_dir:
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    backup_path = backup_dir / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
                    shutil.copy2(file_path, backup_path)
                    result['backup_path'] = str(backup_path)
                
                # Write updated file
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(matches, f, ensure_ascii=False, indent=2)
            
            result['migrated'] = True
    
    except Exception as e:
        result['errors'].append(str(e))
    
    return result


def main():
    """Main migration script."""
    parser = argparse.ArgumentParser(
        description='Migrate job match files to use full URLs'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--backup-dir',
        type=str,
        default='job_matches/backups',
        help='Directory for backups (default: job_matches/backups)'
    )
    
    args = parser.parse_args()
    
    # Get script directory (project root)
    project_root = Path(__file__).parent
    matches_dir = project_root / 'job_matches'
    backup_dir = project_root / args.backup_dir
    
    if not matches_dir.exists():
        print(f"Error: Directory not found: {matches_dir}")
        sys.exit(1)
    
    # Find all match files
    match_files = list(matches_dir.glob('job_matches_*.json'))
    
    if not match_files:
        print(f"No match files found in {matches_dir}")
        sys.exit(0)
    
    print(f"Found {len(match_files)} match file(s) to process")
    if args.dry_run:
        print("DRY RUN MODE - No files will be modified\n")
    else:
        print(f"Backups will be saved to: {backup_dir}\n")
    
    # Process each file
    total_files = 0
    migrated_files = 0
    already_migrated = 0
    total_matches_updated = 0
    errors = []
    
    for file_path in match_files:
        total_files += 1
        print(f"Processing: {file_path.name}...", end=' ')
        
        result = migrate_match_file(
            file_path,
            dry_run=args.dry_run,
            backup_dir=backup_dir if not args.dry_run else None
        )
        
        if result['errors']:
            print(f"ERROR")
            for error in result['errors']:
                print(f"  ✗ {error}")
                errors.append(f"{file_path.name}: {error}")
        elif result['already_migrated']:
            print("SKIPPED (already migrated)")
            already_migrated += 1
        elif result['migrated']:
            print(f"SUCCESS ({result['matches_updated']} URLs updated)")
            migrated_files += 1
            total_matches_updated += result['matches_updated']
            if 'backup_path' in result:
                print(f"  Backup: {Path(result['backup_path']).name}")
        else:
            print("NO CHANGES NEEDED")
    
    # Print summary
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"Total files processed:        {total_files}")
    print(f"Files migrated:               {migrated_files}")
    print(f"Files already migrated:       {already_migrated}")
    print(f"Files with no changes:        {total_files - migrated_files - already_migrated}")
    print(f"Total URLs updated:           {total_matches_updated}")
    
    if errors:
        print(f"\nErrors encountered:           {len(errors)}")
        for error in errors:
            print(f"  ✗ {error}")
    
    if args.dry_run:
        print("\nDRY RUN COMPLETE - No files were modified")
    else:
        print("\nMIGRATION COMPLETE")
    
    print("=" * 60)


if __name__ == '__main__':
    main()
