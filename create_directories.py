import os

# Create necessary directories for the CV to HTML converter feature
directories = [
    'process_cv/cv-data/html',
    'process_cv/cv-data/input',
    'process_cv/cv-data/processed'
]

for directory in directories:
    os.makedirs(directory, exist_ok=True)
    print(f"Created directory: {directory}")

print("All necessary directories have been created.")
