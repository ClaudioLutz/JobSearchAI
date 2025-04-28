"""
Script to move potentially unused files to a 'deprecated' directory.
This is safer than directly deleting them, allowing for easy recovery if needed.
"""

import os
import shutil
from pathlib import Path
import datetime

# Files identified as potentially unused
files_to_move = [
    "test.py",
    "create_directories.py",
    "test_word_template.py",
    "future_low_effort_features.md"
]

# Create timestamp for the deprecated directory
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
deprecated_dir = Path(f"deprecated_{timestamp}")

def main():
    """Move unused files to a timestamped deprecated directory."""
    print(f"Creating deprecated directory: {deprecated_dir}")
    
    # Create the deprecated directory if it doesn't exist
    deprecated_dir.mkdir(exist_ok=True)
    
    # Create a log file to document what was moved
    with open(deprecated_dir / "README.md", "w") as f:
        f.write(f"# Deprecated Files\n\n")
        f.write(f"These files were moved to this directory on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ")
        f.write(f"because they were identified as potentially unused after the code optimization process.\n\n")
        f.write(f"See 'unused_files_report.md' in the main directory for detailed explanations.\n\n")
        f.write(f"## Files\n\n")
    
    # Move each file to the deprecated directory
    moved_files = []
    for file_path in files_to_move:
        if os.path.exists(file_path):
            try:
                # Get the destination path
                dest_path = deprecated_dir / file_path
                
                # Create parent directories if needed
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Move the file
                shutil.move(file_path, dest_path)
                print(f"Moved: {file_path} -> {dest_path}")
                moved_files.append(file_path)
                
                # Update the log
                with open(deprecated_dir / "README.md", "a") as f:
                    f.write(f"- `{file_path}`: Successfully moved\n")
            except Exception as e:
                print(f"ERROR moving {file_path}: {e}")
                with open(deprecated_dir / "README.md", "a") as f:
                    f.write(f"- `{file_path}`: Failed to move - {str(e)}\n")
        else:
            print(f"File not found: {file_path}")
            with open(deprecated_dir / "README.md", "a") as f:
                f.write(f"- `{file_path}`: File not found\n")
    
    # Summary
    if moved_files:
        print(f"\nSuccessfully moved {len(moved_files)} files to {deprecated_dir}")
        print("To restore any file, use: mv deprecated_TIMESTAMP/filename .")
    else:
        print("\nNo files were moved.")

if __name__ == "__main__":
    main()
