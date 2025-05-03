# JobsearchAI - User Guide

Welcome to JobsearchAI, your personal assistant for streamlining the job application process!

## Overview

JobsearchAI helps you:
*   Process your CV to extract key skills and experience.
*   Scrape job listings from supported websites (e.g., ostjob.ch).
*   Match your profile against job requirements using AI.
*   Generate personalized motivation letters and email texts.
*   Manage your application documents.

## Installation

**Prerequisites:**
*   An OpenAI API Key is **required** for the AI features. You can obtain one from [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys). Note that using the OpenAI API may incur costs based on your usage.

**Installation Steps:**

### Windows
1.  Download the `JobsearchAI-Installer.exe` file from the [**Releases Page**](https://github.com/your_repo/JobsearchAI/releases) (Replace with actual link).
2.  Run the installer (`JobsearchAI-Installer.exe`). You might see a security warning from Windows; click "More info" and then "Run anyway" if you trust the source.
3.  Follow the installation prompts.
4.  Once installed, you can find JobsearchAI in your Start Menu or Desktop shortcut.

### macOS
1.  Download the `JobsearchAI.dmg` file from the [**Releases Page**](https://github.com/your_repo/JobsearchAI/releases) (Replace with actual link).
2.  Open the downloaded `.dmg` file.
3.  Drag the `JobsearchAI.app` icon into your `Applications` folder.
4.  You may need to grant permission to run the app the first time: Right-click (or Control-click) the `JobsearchAI.app` in your Applications folder and select "Open". Confirm you want to open it in the security dialog.
5.  You can now launch JobsearchAI from your Applications folder or Launchpad.

### Linux (General Instructions)
1.  Download the `JobsearchAI_Linux` executable or archive from the [**Releases Page**](https://github.com/your_repo/JobsearchAI/releases) (Replace with actual link).
2.  Extract the archive if necessary.
3.  Make the main executable file runnable: `chmod +x JobsearchAI_Linux` (adjust filename if needed).
4.  Run the application: `./JobsearchAI_Linux`

## First-Time Setup

When you launch JobsearchAI for the first time, a setup wizard will appear:

1.  **OpenAI API Key:** Enter your OpenAI API key (it starts with `sk-...`). This is mandatory for the application to work. Your key will be stored securely using your operating system's credential manager if possible.
2.  **Data Directory (Optional):** Choose where JobsearchAI will store your data (CVs, job data files, generated letters, logs). The default location is usually best, but you can specify a custom path if needed.

Click "Complete Setup" to save your configuration.

## Basic Usage

Once set up, the main dashboard provides access to all features:

1.  **Setup & Data Tab:** Upload your CV (PDF format) and run the job scraper.
2.  **Run Process Tab:** Run the job matcher to compare your CV against scraped jobs, or run the combined scraping and matching process.
3.  **View Files Tab:** Manage your uploaded CVs, view scraped job data, access generated job match reports, and view/download generated motivation letters.
4.  **Configuration Tab:** Update your OpenAI API key or change the data directory after the initial setup.

## Getting Help

If you encounter issues:
*   Ensure you have entered a valid OpenAI API key in the Configuration tab.
*   Check that you have an active internet connection (required for API calls and scraping).
*   Review the logs stored in the `logs` subfolder within your chosen data directory.
*   Consult the full documentation (link to be added).
*   Contact support: [your-support-email@example.com](mailto:your-support-email@example.com) (Replace with actual email).

## Privacy & Security

*   All your personal data (CVs, generated letters, etc.) is stored **locally** on your computer in the data directory you configured.
*   Your OpenAI API key is stored securely using your operating system's credential manager (like Windows Credential Manager or macOS Keychain) when possible, falling back to an encrypted local file otherwise.
*   JobsearchAI only communicates externally to make API calls to OpenAI using your key. No other data is sent to external servers.

---
Thank you for using JobsearchAI!
