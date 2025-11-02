"""
Database backup utility for JobSearchAI SQLite database.

Creates timestamped backups and manages backup retention.
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def backup_database(
    db_path="instance/jobsearchai.db",
    backup_dir="backups",
    keep=10
):
    """
    Create timestamped backup of database
    
    Args:
        db_path: Path to source database
        backup_dir: Directory to store backups
        keep: Number of recent backups to retain
        
    Returns:
        Path to backup file or None if failed
    """
    print("\n" + "="*60)
    print("Database Backup Utility")
    print("="*60 + "\n")
    
    # Validate source database exists
    if not os.path.exists(db_path):
        print(f"❌ Source database not found: {db_path}")
        return None
    
    # Create backup directory
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_name = Path(db_path).stem
    backup_file = f"{backup_dir}/{db_name}_backup_{timestamp}.db"
    
    print(f"📂 Source: {db_path}")
    print(f"💾 Backup: {backup_file}")
    
    # Get source database size
    src_size = os.path.getsize(db_path)
    print(f"📊 Size:   {src_size:,} bytes ({src_size / (1024*1024):.2f} MB)")
    
    # Create backup using SQLite .backup command
    try:
        print("\n🔄 Creating backup...")
        
        src_conn = sqlite3.connect(db_path)
        dst_conn = sqlite3.connect(backup_file)
        
        # Use SQLite backup API
        src_conn.backup(dst_conn)
        
        src_conn.close()
        dst_conn.close()
        
        # Verify backup was created
        if os.path.exists(backup_file):
            backup_size = os.path.getsize(backup_file)
            print(f"✅ Backup created successfully")
            print(f"   Size: {backup_size:,} bytes ({backup_size / (1024*1024):.2f} MB)")
            
            # Cleanup old backups
            cleanup_old_backups(backup_dir, keep, db_name)
            
            print(f"\n{'='*60}")
            print("Backup Complete")
            print(f"{'='*60}\n")
            
            return backup_file
        else:
            print("❌ Backup file was not created")
            return None
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def cleanup_old_backups(backup_dir, keep, db_name):
    """
    Remove old backups, keeping only the most recent N
    
    Args:
        backup_dir: Directory containing backups
        keep: Number of backups to keep
        db_name: Database name to filter backups
    """
    # Find all backups for this database
    pattern = f"{db_name}_backup_*.db"
    backup_path = Path(backup_dir)
    backups = sorted(backup_path.glob(pattern))
    
    if len(backups) > keep:
        to_remove = backups[:-keep]
        
        print(f"\n🧹 Cleaning up old backups (keeping last {keep})...")
        
        for backup in to_remove:
            try:
                backup_size = backup.stat().st_size
                backup.unlink()
                print(f"  🗑️  Removed: {backup.name} ({backup_size:,} bytes)")
            except Exception as e:
                print(f"  ⚠️  Failed to remove {backup.name}: {e}")
        
        print(f"✅ Cleanup complete - {len(to_remove)} old backups removed")
    else:
        print(f"\n✓ No cleanup needed - {len(backups)} backups exist (keep: {keep})")


def list_backups(backup_dir="backups", db_name="jobsearchai"):
    """
    List all available backups for a database
    
    Args:
        backup_dir: Directory containing backups
        db_name: Database name to filter backups
    """
    print("\n" + "="*60)
    print(f"Available Backups for {db_name}")
    print("="*60 + "\n")
    
    pattern = f"{db_name}_backup_*.db"
    backup_path = Path(backup_dir)
    
    if not backup_path.exists():
        print(f"❌ Backup directory not found: {backup_dir}")
        return
    
    backups = sorted(backup_path.glob(pattern), reverse=True)
    
    if not backups:
        print(f"No backups found matching pattern: {pattern}")
        return
    
    print(f"Found {len(backups)} backup(s):\n")
    
    for i, backup in enumerate(backups, 1):
        stats = backup.stat()
        size_mb = stats.st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(stats.st_mtime)
        
        print(f"{i}. {backup.name}")
        print(f"   Size:     {size_mb:.2f} MB")
        print(f"   Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print()


def restore_backup(backup_file, db_path="instance/jobsearchai.db", confirm=True):
    """
    Restore database from backup
    
    Args:
        backup_file: Path to backup file
        db_path: Path to destination database
        confirm: If True, require user confirmation
        
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "="*60)
    print("Database Restore Utility")
    print("="*60 + "\n")
    
    # Validate backup exists
    if not os.path.exists(backup_file):
        print(f"❌ Backup file not found: {backup_file}")
        return False
    
    print(f"📂 Backup:  {backup_file}")
    print(f"💾 Restore to: {db_path}")
    
    # Check if destination exists
    if os.path.exists(db_path):
        current_size = os.path.getsize(db_path)
        print(f"⚠️  Warning: Destination database exists ({current_size:,} bytes)")
        
        if confirm:
            response = input("\n❓ Overwrite existing database? (yes/no): ").strip().lower()
            if response != 'yes':
                print("❌ Restore cancelled by user")
                return False
    
    backup_size = os.path.getsize(backup_file)
    print(f"📊 Backup size: {backup_size:,} bytes ({backup_size / (1024*1024):.2f} MB)")
    
    try:
        print("\n🔄 Restoring from backup...")
        
        # Create backup of current database if it exists
        if os.path.exists(db_path):
            temp_backup = f"{db_path}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(db_path, temp_backup)
            print(f"✓ Current database backed up to: {temp_backup}")
        
        # Restore by copying backup
        import shutil
        shutil.copy2(backup_file, db_path)
        
        # Verify restore
        if os.path.exists(db_path):
            restored_size = os.path.getsize(db_path)
            print(f"✅ Restore successful")
            print(f"   Size: {restored_size:,} bytes ({restored_size / (1024*1024):.2f} MB)")
            
            print(f"\n{'='*60}")
            print("Restore Complete")
            print(f"{'='*60}\n")
            
            return True
        else:
            print("❌ Restore failed - destination file not created")
            return False
            
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Database backup and restore utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create backup
  python scripts/backup_database.py
  
  # List all backups
  python scripts/backup_database.py --list
  
  # Restore from specific backup
  python scripts/backup_database.py --restore backups/jobsearchai_backup_20251102_120000.db
        """
    )
    
    parser.add_argument(
        '--db-path',
        default='instance/jobsearchai.db',
        help='Path to database (default: instance/jobsearchai.db)'
    )
    
    parser.add_argument(
        '--backup-dir',
        default='backups',
        help='Directory for backups (default: backups)'
    )
    
    parser.add_argument(
        '--keep',
        type=int,
        default=10,
        help='Number of backups to keep (default: 10)'
    )
    
    parser.add_argument(
        '--list',
        action='store_true',
        help='List available backups'
    )
    
    parser.add_argument(
        '--restore',
        metavar='BACKUP_FILE',
        help='Restore from specified backup file'
    )
    
    parser.add_argument(
        '--no-confirm',
        action='store_true',
        help='Skip confirmation prompts (use with caution)'
    )
    
    args = parser.parse_args()
    
    try:
        if args.list:
            # List available backups
            db_name = Path(args.db_path).stem
            list_backups(args.backup_dir, db_name)
            
        elif args.restore:
            # Restore from backup
            success = restore_backup(
                args.restore,
                args.db_path,
                confirm=not args.no_confirm
            )
            sys.exit(0 if success else 1)
            
        else:
            # Create backup
            result = backup_database(
                args.db_path,
                args.backup_dir,
                args.keep
            )
            sys.exit(0 if result else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Operation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
