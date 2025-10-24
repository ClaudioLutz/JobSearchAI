# JobSearchAI - User Quick Start Guide

**Created:** 2025-10-16  
**For:** End Users (Job Seekers)

---

## 🚀 How to Use Your Application RIGHT NOW

Your JobSearchAI application is **already working**! Here's how to use it today:

### Step 1: Start the Application (5 minutes)

```bash
# 1. Open terminal in your project folder
cd c:/Codes/JobsearchAI/JobSearchAI

# 2. Make sure dependencies are installed
pip install -r requirements.txt

# 3. Initialize the database (first time only)
python init_db.py

# 4. Start the application
python dashboard.py
```

### Step 2: Access the Dashboard

1. Open your web browser
2. Go to: `http://localhost:5000`
3. **Register** a new account (or login if you already have one)
4. You're in! 🎉

---

## 📋 Your Morning Job Search Workflow

### **The Complete Job Search Process** (What the app does for you)

1. **Upload Your CV** (Setup & Data tab)
   - Click "Browse" → Select your PDF CV
   - Click "Upload CV"
   - The AI extracts and summarizes your experience

2. **Scrape Job Listings** (Setup & Data tab)
   - Set "Maximum Pages to Scrape" (e.g., 50)
   - Click "Run Job Scraper"
   - Wait ~2-5 minutes while it scrapes ostjob.ch
   - Job listings saved to `job-data-acquisition/data/`

3. **Match Jobs to Your Profile** (Run Process tab)
   - Select your CV from dropdown
   - Set matching parameters:
     - Minimum Match Score: 3 (1-10 scale)
     - Max Jobs to Process: 50
     - Max Results to Return: 10
   - Click "Run Job Matcher"
   - AI analyzes each job against your CV
   - Results saved to `job_matches/`

4. **Generate Motivation Letters** (View Files tab → Motivation Letters section)
   - View matched jobs
   - Select a job
   - Click "Generate Letter"
   - AI creates personalized letter + email text
   - Downloads as Word document

5. **📧 NEW! Application Queue** (Application Queue button - NEW feature)
   - **Review pending applications** with validation scores
   - **Preview email** before sending
   - **Send applications** directly from dashboard
   - **Track sent/failed** applications automatically

---

## 🎯 What Each Tab Does

### **Setup & Data Tab**
- **Upload CV**: Add your resume (PDF format)
- **Job Data Acquisition**: Scrape job listings from ostjob.ch
- Purpose: Get fresh job data into the system

### **Run Process Tab**
- **Run Job Matcher**: Match jobs to your CV
- **Run Combined Process**: Scrape + Match in one go
- Purpose: Find jobs that fit your profile

### **View Files Tab**
- View uploaded CVs
- View scraped job data
- View match reports
- Generate motivation letters
- Purpose: Access all your generated content

### **📧 Application Queue** (NEW!)
- Review applications before sending
- Validate email/letter completeness
- Send emails directly from dashboard
- Track sent/failed applications
- Purpose: Streamline your morning email routine

---

## ⚙️ Configuration Required

### Gmail Setup (for sending applications)

Create `process_cv/.env` file with:

```env
OPENAI_API_KEY=sk-your_openai_api_key_here
SECRET_KEY=your_secret_key_here
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_16_character_app_password
```

**How to get Gmail App Password:**
1. Go to https://myaccount.google.com/
2. Navigate to Security → 2-Step Verification
3. Scroll to "App passwords"
4. Generate new app password for "JobSearchAI"
5. Copy the 16-character code to your .env file

---

## 📁 Where Your Files Are Stored

```
JobSearchAI/
├── job-data-acquisition/data/     # Scraped job listings (JSON)
├── job_matches/                    # Match reports (MD + JSON)
│   ├── pending/                    # Ready to apply
│   ├── sent/                       # Successfully sent
│   └── failed/                     # Failed sends (with errors)
├── motivation_letters/             # Generated letters (HTML + DOCX)
├── process_cv/cv-data/
│   ├── input/                      # Your uploaded CVs
│   └── processed/                  # CV summaries
└── instance/                       # User database
```

---

## 🔧 Troubleshooting

### "No module named 'flask'"
```bash
pip install -r requirements.txt
```

### "Database not found"
```bash
python init_db.py
```

### "OpenAI API Error"
- Check your `.env` file has valid `OPENAI_API_KEY`
- Verify you have API credits: https://platform.openai.com/account/usage

### "Job scraper not working"
- Check `job-data-acquisition/settings.json`
- Verify ScrapeGraphAI configuration
- Check logs in `job-data-acquisition/logs/`

### "Email not sending"
- Verify Gmail app password in `.env`
- Ensure 2-Step Verification is enabled on Google account
- Check `GMAIL_ADDRESS` matches your actual Gmail

---

## 🎯 Your Typical Morning Routine

**Scenario:** You want to apply to 5 jobs this morning

1. **Launch app**: `python dashboard.py` → `http://localhost:5000`
2. **Scrape jobs** (if you need fresh ones): Setup & Data → Run Job Scraper (50 pages)
3. **Match jobs**: Run Process → Run Job Matcher (select CV, min score 3)
4. **Review matches**: View Files → Check match reports
5. **Generate letters**: View Files → Generate letters for top 5 matches
6. **📧 Send applications**: Application Queue → Review → Send
7. **Track results**: Application Queue → View Sent/Failed tabs

**Time:** 15-30 minutes total (mostly waiting for AI)

---

## 🆕 What's Coming (Future Enhancements)

The documentation you just created (product-brief, tech-spec, ux-spec) describes **three planned enhancements**:

1. **Story 1.1**: Backend Infrastructure ✅ **COMPLETE** (Email + Validation modules)
2. **Story 1.2**: Application Queue UI 🚧 **NEXT** (Visual queue dashboard)
3. **Story 1.3**: Integration & Polish 📋 **PLANNED** (End-to-end testing)

**Status:** Story 1.1 is complete and ready for your review! The email sender and validation modules are implemented with 44/44 tests passing.

---

## 💡 Pro Tips

1. **Batch Processing**: Run scraper overnight → match in morning
2. **Quality Over Quantity**: Set min_score to 4-5 for better matches
3. **Customize Letters**: Edit generated letters before sending
4. **Track Applications**: Use consistent file naming in `job_matches/`
5. **Regular Updates**: Run scraper weekly for fresh jobs

---

## 📞 Need Help?

- **Logs**: Check `dashboard.log` for errors
- **Documentation**: See `Documentation/` folder for technical details
- **Component Docs**: Each component has detailed docs in `Documentation/`

---

**You're ready to go! Start with `python dashboard.py` and let AI find your next job.** 🚀
