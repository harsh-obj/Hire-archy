# Hire-archy: Resume Screening & ATS Optimization Suite

An explainable Applicant Tracking System (ATS) and resume screener built with a Python Django backend and a React, HTML, and CSS frontend.

## Key Features

| Feature | Description |
| :--- | :--- |
| Multi-Format Ingestion | Extracts text from PDF (`pypdf`), Word DOCX (`python-docx` paragraphs and tables), and plain text (`TXT`). |
| Explainable ATS Score | Composite formula: Skill Match (40%) + Semantic Relevance (35%) + Keyword Context (15%) + Structure Health (10%). |
| Skill Gap Analysis | Extracts competencies across 7 technical and soft skill domains with per-domain coverage tables. |
| Interactive Charts | Responsive SVG competency radar chart and top job-description phrase matching bars. |
| ATS Readability Audit | Checks for standard ATS headers, contact metadata, word count balance, action verbs, and quantifiable metrics. |
| Actionable Rewrites | Prioritized edits and Google X-Y-Z bullet guidance. |
| Optional Gemini AI Critique | Optional Google Gemini 2.5 Flash integration for executive summary, bullet rewrites, and interview questions. |
| Plain-Text Report Export | One-click `.txt` audit report download and clipboard copy. |
| Demo Presets | Instant loading for Full Stack Engineer and Machine Learning & AI Engineer demos. |

## Tech Stack

- **Backend & NLP Engine:** Python 3.10+, Django, Scikit-Learn (`TfidfVectorizer`, cosine similarity), NumPy
- **Document Parsing:** `pypdf`, `python-docx`
- **Frontend:** HTML5, CSS3 (lighter sky-blue, white, and black theme), React 18 (vendored locally with zero Node build step)
- **Optional AI Enhancement:** Google Gemini 2.5 Flash via `google-genai`

## Quick Start on Windows

### Option 1: Launcher Scripts
Run either:
```cmd
run_app.bat
```
or in PowerShell:
```powershell
.\run_app.ps1
```

### Option 2: Manual Terminal Execution
1. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
2. Run the automated test suite:
   ```cmd
   python test_ats.py
   ```
3. Start the Django development server:
   ```cmd
   python manage.py runserver
   ```
   Open `http://127.0.0.1:8000` in your browser.

## Repository Structure

```text
Hire-archy-master/
├── manage.py               # Django management entrypoint (runserver, check)
├── hirearchy_site/
│   ├── __init__.py
│   ├── settings.py         # Django settings and static frontend configuration
│   ├── urls.py             # Root URL routing
│   ├── wsgi.py             # WSGI entrypoint
│   └── asgi.py             # ASGI entrypoint
├── ats/
│   ├── __init__.py
│   ├── apps.py
│   ├── engine.py           # Core NLP, parsing, scoring, and report generation
│   ├── urls.py             # ATS API and index URL patterns
│   └── views.py            # Django views serving API endpoints and React UI
├── frontend/
│   ├── index.html          # HTML entrypoint loading React and CSS
│   ├── styles.css          # Responsive sky-blue, white, and black theme
│   ├── app.jsx             # React UI components and SVG charts
│   └── vendor/             # Offline React 18 and Babel standalone bundles
├── main.py                 # Facade re-exporting engine functions and WSGI app
├── test_ats.py             # Unit and Django integration test suite
├── generate_samples.py     # Sample PDF, DOCX, and TXT resume generator
├── requirements.txt        # Python package dependencies
├── run_app.bat             # Windows batch launcher
├── run_app.ps1             # Windows PowerShell launcher
└── sample_resumes/         # Sample candidate resumes
```

## License
Open-source under the MIT License.
