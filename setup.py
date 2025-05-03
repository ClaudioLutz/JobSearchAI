from setuptools import setup, find_packages
import os

# Function to read requirements from requirements.txt
def parse_requirements(filename='requirements.txt'):
    """Load requirements from a pip requirements file."""
    try:
        with open(filename, 'r') as f:
            # Filter out comments and empty lines
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            # Remove any version specifiers for setup.py (optional, depends on strategy)
            # For simplicity here, we keep them if they exist
            return lines
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Falling back to listed dependencies.")
        # Fallback list if requirements.txt is missing
        return [
            "Flask>=2.0",
            "openai>=1.0", # Specify appropriate version
            "python-dotenv",
            "requests",
            "beautifulsoup4",
            "PyMuPDF", # fitz
            "docxtpl",
            "python-docx", # docxtpl dependency
            "keyring", # For secure API key storage
            "appdirs", # For OS-specific user directories
            # Add other direct dependencies if not captured by requirements.txt
            # e.g., scrapegraphai if used directly and not just in sub-project
        ]

# Read the contents of your README file
this_directory = os.path.abspath(os.path.dirname(__file__))
try:
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        long_description = f.read()
except FileNotFoundError:
    long_description = "JobsearchAI: AI-powered job matching and application assistance."

setup(
    name="JobsearchAI",
    version="1.0.0", # Consider using a versioning scheme
    author="Your Name / Company Name", # Replace with actual author
    author_email="your.email@example.com", # Replace with actual email
    description="AI-powered job matching and application assistance tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your_repo/JobsearchAI", # Replace with your repo URL
    packages=find_packages(exclude=["tests*", "job-data-acquisition"]), # Exclude tests and sub-projects if managed separately
    include_package_data=True, # Include files specified in MANIFEST.in (like templates, static)
    install_requires=parse_requirements(),
    python_requires='>=3.8', # Specify minimum Python version
    entry_points={
        # This allows running 'jobsearchai' command after pip install
        # For PyInstaller, the main script is specified in the .spec file
        "console_scripts": [
            "jobsearchai=dashboard:main", # Assuming dashboard.py has a main() function or similar entry
        ],
        # If using Flask CLI commands
        # "flask.commands": [
        #     "my_command=jobsearchai.commands:cli",
        # ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License", # Choose your license
        "Operating System :: OS Independent",
        "Framework :: Flask",
        "Topic :: Office/Business :: Scheduling", # Adjust topic as needed
        "Private :: Do Not Upload", # If not intended for PyPI
    ],
    keywords='job search ai flask automation cv resume cover letter',
    # Add project_urls if desired
    # project_urls={
    #     'Bug Reports': 'https://github.com/your_repo/JobsearchAI/issues',
    #     'Source': 'https://github.com/your_repo/JobsearchAI/',
    # },
)
