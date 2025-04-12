# JobsearchAI

A system that matches job listings with candidate CVs using AI-powered semantic matching.

## Components

The system consists of three main components:

1. **Job Data Acquisition**: Scrapes job listings from ostjob.ch and saves them in a structured JSON format.
2. **CV Processor**: Extracts and summarizes information from candidate CVs.
3. **Job Matcher**: Matches job listings with candidate profiles using semantic understanding.

## How It Works

### Data Preparation Phase

1. **CV Processing**: The system extracts structured information from the candidate's CV, including skills, experience, education, and preferences.
2. **Job Data Collection**: The system gathers current job listings from ostjob.ch.

### Matching Engine

The matching engine uses a semantic approach rather than simple keyword matching:

1. It loads the processed CV summary and the scraped job data.
2. For each job listing, it uses a ChatGPT model to evaluate:
   - How well the candidate's skills match the job requirements
   - Whether the candidate's experience level is appropriate
   - If the location preferences align
   - How well the candidate's education matches the requirements
   - Overall suitability score on a scale of 1-10

### Results Processing

1. Jobs are ranked by overall match score.
2. Jobs below a certain threshold (e.g., scores below 6) are filtered out.
3. A report is generated with the top matches, including the reasoning for each match.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/JobsearchAI.git
   cd JobsearchAI
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key in `process_cv/.env`:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Usage

### Running the Job Matcher

```python
python job_matcher.py
```

This will:
1. Process the CV located at `process_cv/cv-data/Lebenslauf_Claudio Lutz.pdf`
2. Match it with the latest job data
3. Generate a report with the top matches

### Customizing the Matching

You can modify the following parameters in `job_matcher.py`:

- `min_score`: Minimum overall match score (default: 6)
- `max_results`: Maximum number of results to include in the report (default: 10)
- `cv_path`: Path to the CV file

## Output

The system generates two output files:

1. A JSON file with detailed match information
2. A Markdown report with the top job matches, including:
   - Job title and company
   - Overall match score
   - Skills match score
   - Experience match score
   - Education fit score
   - Location compatibility
   - Reasoning for the match
   - Application URL

## Future Improvements

- Web interface for uploading CVs and viewing matches
- Support for multiple CV formats
- More detailed skill matching using domain-specific knowledge
- Integration with job application systems
