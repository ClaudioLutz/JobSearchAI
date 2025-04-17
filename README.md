# JobsearchAI

A system that matches job listings with candidate CVs using AI-powered semantic matching.

## Components

The system consists of four main components:

1. **Job Data Acquisition**: Scrapes job listings from ostjob.ch and saves them in a structured JSON format.
2. **CV Processor**: Extracts and summarizes information from candidate CVs.
3. **Job Matcher**: Matches job listings with candidate profiles using semantic understanding.
4. **Motivation Letter Generator**: Creates personalized motivation letters based on the candidate's CV and job details.

## How It Works

### Data Preparation Phase

1. **CV Processing**: The system extracts structured information from the candidate's CV, including:
   - Skills and technical competencies
   - Work experience and history
   - Education and qualifications
   - Location preferences
   - Career trajectory and evolution
   - Job preferences (industry, company size, work environment)
   - Career goals and aspirations
   - Work values and cultural preferences
2. **Job Data Collection**: The system gathers current job listings from ostjob.ch.

### Matching Engine

The matching engine uses a semantic approach rather than simple keyword matching:

1. It loads the processed CV summary and the scraped job data.
2. For each job listing, it uses a ChatGPT model to evaluate:
   - How well the candidate's skills match the job requirements
   - Whether the candidate's experience level is appropriate
   - If the location preferences align
   - How well the candidate's education matches the requirements
   - How well the job aligns with the candidate's career trajectory
   - How well the job matches the candidate's preferences
   - How likely the candidate would be satisfied in this position
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

### Using the Dashboard

```python
python dashboard.py
```

This will:
1. Start the Flask web server at http://localhost:5000
2. Provide a web interface for interacting with all components of the system

The dashboard allows you to:
- Upload and process CVs
- Run the job matcher with a selected CV
- Run the job scraper to get new job listings
- View job match results
- Generate motivation letters for specific job postings

### Generating Motivation Letters

Motivation letters can be generated through the dashboard:
1. View job match results
2. Click the "Motivationsschreiben erstellen" button next to a job listing
3. The system will:
   - Extract detailed job information from the website
   - Create a personalized motivation letter based on your CV and the job details
   - Display the letter in a new page with options to print or download

## Output

The system generates two output files:

1. A JSON file with detailed match information
2. A Markdown report with the top job matches, including:
   - Job title and company
   - Overall match score
   - Skills match score
   - Experience match score
   - Education fit score
   - Career trajectory alignment score
   - Preference match score
   - Potential satisfaction score
   - Location compatibility
   - Reasoning for the match
   - Application URL

## Future Improvements

- Support for multiple CV formats beyond PDF and DOCX
- More detailed skill matching using domain-specific knowledge
- Integration with job application systems for direct applications
- Enhanced preference analysis using historical job satisfaction data
- Personalized career path recommendations based on career trajectory
- Feedback mechanism to improve preference and satisfaction predictions
- Visualization of career trajectory and potential future paths
- Customizable weighting of different matching factors (skills vs. satisfaction)
- Integration with company culture databases for better cultural fit assessment
