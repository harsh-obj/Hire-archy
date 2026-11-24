"""
ats/engine.py
-------------
Core ATS and NLP backend engine for Hire-archy.

Provides:
- Document extraction for PDF, DOCX, and TXT
- Candidate metadata and contact extraction
- ATS structural readability auditing
- Curated multi-domain skill taxonomy extraction and TF-IDF n-gram analysis
- Semantic similarity via SBERT (optional) or sublinear TF-IDF cosine similarity
- Explainable weighted composite ATS scoring
- Actionable resume optimization suggestions and plain-text audit export
- Optional Google Gemini AI deep critique
"""

import io
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import pypdf
    PYPDF_ENABLED = True
except ImportError:
    PYPDF_ENABLED = False

try:
    import docx
    DOCX_ENABLED = True
except ImportError:
    DOCX_ENABLED = False

try:
    from sentence_transformers import SentenceTransformer, util
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    SBERT_ENABLED = True
except Exception:
    SBERT_ENABLED = False
    embedder = None

try:
    from google import genai
    from google.genai import types
    GEMINI_ENABLED = True
except ImportError:
    GEMINI_ENABLED = False


SKILL_TAXONOMY: Dict[str, List[str]] = {
    "Languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "c", "ruby",
        "golang", "go", "rust", "php", "swift", "kotlin", "r", "sql", "html",
        "html5", "css", "css3", "sass", "bash", "shell", "powershell", "scala",
        "dart", "perl", "matlab",
    ],
    "Frameworks & Libraries": [
        "react", "react.js", "next.js", "vue", "vue.js", "angular", "node.js",
        "express", "express.js", "django", "flask", "fastapi", "spring",
        "spring boot", "asp.net", ".net", ".net core", "ruby on rails", "laravel",
        "tailwind", "tailwindcss", "bootstrap", "redux", "graphql", "jquery",
        "svelte", "nestjs", "pytorch", "tensorflow", "keras", "scikit-learn",
        "pandas", "numpy", "scipy", "opencv", "hugging face", "langchain",
    ],
    "Databases & Storage": [
        "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
        "cassandra", "dynamodb", "oracle", "sql server", "neo4j", "elasticsearch",
        "firebase", "supabase", "snowflake", "bigquery", "mariadb", "couchdb",
    ],
    "Cloud & DevOps": [
        "aws", "amazon web services", "azure", "microsoft azure", "google cloud",
        "gcp", "docker", "kubernetes", "k8s", "ci/cd", "github actions",
        "gitlab ci", "jenkins", "terraform", "ansible", "linux", "unix",
        "nginx", "apache", "helm", "prometheus", "grafana", "serverless",
        "cloudformation", "circleci",
    ],
    "AI, ML & Data": [
        "machine learning", "deep learning", "nlp", "natural language processing",
        "computer vision", "llm", "large language models", "data analysis",
        "data visualization", "matplotlib", "seaborn", "tableau", "power bi",
        "powerbi", "transformers", "generative ai", "neural networks", "bert",
        "rag", "prompt engineering", "feature engineering",
    ],
    "Software Engineering Concepts": [
        "restful api", "rest api", "microservices", "oop", "object-oriented programming",
        "data structures", "algorithms", "system design", "agile", "scrum", "kanban",
        "tdd", "unit testing", "integration testing", "git", "github", "gitlab",
        "version control", "websockets", "mvc", "design patterns", "ci cd",
    ],
    "Soft Skills & Leadership": [
        "communication", "leadership", "problem solving", "critical thinking",
        "team collaboration", "teamwork", "project management", "time management",
        "mentorship", "adaptability", "public speaking", "stakeholder management",
        "presentation", "analytical skills", "negotiation", "conflict resolution",
    ],
    "Product & Strategy": [
        "product roadmap", "product strategy", "user research", "customer discovery",
        "backlog management", "user stories", "go-to-market", "a/b testing",
        "kpi tracking", "prioritization", "wireframing", "cross-functional",
        "competitive analysis", "product metrics", "sprint planning", "product launch",
    ],
}

ALL_ONTOLOGY_SKILLS: List[str] = sorted(
    {skill for skills in SKILL_TAXONOMY.values() for skill in skills},
    key=lambda item: -len(item),
)


def extract_text_from_file(file_input: Any, filename_hint: Optional[str] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Extract text and document metadata from a file-like object, file path, or bytes buffer.
    Supports PDF (pypdf), DOCX (python-docx), and plain text.
    """
    filename = (filename_hint or "unknown").lower()
    file_bytes: bytes = b""

    if hasattr(file_input, "name") and hasattr(file_input, "read"):
        filename = os.path.basename(str(file_input.name)).lower()
        file_bytes = file_input.read()
        if hasattr(file_input, "seek"):
            file_input.seek(0)
    elif isinstance(file_input, str):
        filename = os.path.basename(file_input).lower()
        with open(file_input, "rb") as handle:
            file_bytes = handle.read()
    elif isinstance(file_input, (bytes, io.BytesIO)):
        if not filename_hint:
            filename = "document.pdf"
        file_bytes = file_input.getvalue() if isinstance(file_input, io.BytesIO) else file_input

    raw_text = ""
    pages_count = 1
    doc_type = "txt"

    if filename.endswith(".pdf"):
        doc_type = "pdf"
        if not PYPDF_ENABLED:
            raise RuntimeError("pypdf library is required to extract PDF files.")
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages_count = len(reader.pages)
            extracted = [page.extract_text() for page in reader.pages if page.extract_text()]
            raw_text = "\n".join(extracted)
        except Exception as exc:
            raw_text = f"Error reading PDF: {exc}"

    elif filename.endswith(".docx"):
        doc_type = "docx"
        if not DOCX_ENABLED:
            raise RuntimeError("python-docx library is required to extract DOCX files.")
        try:
            document = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        paragraphs.append(" | ".join(row_text))
            raw_text = "\n".join(paragraphs)
            pages_count = max(1, len(paragraphs) // 30)
        except Exception as exc:
            raw_text = f"Error reading DOCX: {exc}"

    else:
        try:
            raw_text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = str(file_bytes)

    words = raw_text.split()
    metadata = {
        "filename": filename,
        "file_type": doc_type,
        "word_count": len(words),
        "char_count": len(raw_text),
        "estimated_pages": pages_count,
    }
    return raw_text, metadata


def clean_text(text: str) -> str:
    """
    Normalize text while preserving technical tokens such as c++, c#, .net, node.js, vue.js, and react.js.
    """
    if not text or not isinstance(text, str):
        return ""

    text = text.replace("\r", " ").replace("\t", " ")
    token_map = [
        (r"c\+\+", "cplusplus", "c++"),
        (r"c\#", "csharp", "c#"),
        (r"\.net", "dotnet", ".net"),
        (r"node\.js", "nodejs", "node.js"),
        (r"vue\.js", "vuejs", "vue.js"),
        (r"react\.js", "reactjs", "react.js"),
    ]
    for pattern, placeholder, _ in token_map:
        text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)

    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    for _, placeholder, original in token_map:
        text = re.sub(placeholder, original, text)

    return re.sub(r"\s+", " ", text).lower().strip()


def extract_candidate_metadata(text: str) -> Dict[str, Any]:
    """Extract candidate name, email, phone, LinkedIn, and GitHub links from resume text."""
    emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    phones = re.findall(r"(?:(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}", text)
    valid_phones = [p.strip() for p in phones if len(re.sub(r"\D", "", p)) >= 10][:2]

    linkedin = re.findall(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", text, re.IGNORECASE)
    github = re.findall(r"(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+", text, re.IGNORECASE)

    candidate_name = "Candidate"
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    skip_tokens = ("@", "http", "www", "github", "linkedin", "resume", "curriculum", "page")

    for line in lines[:8]:
        if any(token in line.lower() for token in skip_tokens):
            continue
        cleaned_line = re.sub(r"[^a-zA-Z\s]", "", line).strip()
        words = cleaned_line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            candidate_name = cleaned_line
            break
        if len(words) == 1 and words[0].isupper():
            candidate_name = cleaned_line
            break

    return {
        "candidate_name": candidate_name,
        "email": emails[0] if emails else None,
        "phone": valid_phones[0] if valid_phones else None,
        "linkedin": linkedin[0] if linkedin else None,
        "github": github[0] if github else None,
    }


def audit_resume_structure(text: str) -> Dict[str, Any]:
    """Audit standard ATS sections, action verbs, quantifiable metrics, and word density."""
    lower = text.lower()

    standard_sections = {
        "Summary / Objective": bool(re.search(r"\b(summary|objective|profile|about me)\b", lower)),
        "Work Experience": bool(re.search(r"\b(experience|work history|employment|internship|professional experience)\b", lower)),
        "Education": bool(re.search(r"\b(education|academic|degree|university|bachelor|master|b\.tech|m\.tech|gpa)\b", lower)),
        "Skills": bool(re.search(r"\b(skills|technical skills|technologies|proficiencies|core competencies)\b", lower)),
        "Projects": bool(re.search(r"\b(projects|personal projects|academic projects|key projects)\b", lower)),
        "Certifications": bool(re.search(r"\b(certifications|certificate|licenses|credentials|courses)\b", lower)),
    }

    detected_count = sum(1 for present in standard_sections.values() if present)
    total_sections = len(standard_sections)
    section_health_pct = int((detected_count / total_sections) * 100)

    action_verbs = [
        "led", "developed", "engineered", "built", "designed", "implemented",
        "optimized", "increased", "reduced", "delivered", "managed", "architected",
        "created", "spearheaded", "accelerated", "boosted", "deployed", "scaled",
    ]
    detected_verbs = [verb for verb in action_verbs if re.search(r"\b" + verb + r"\b", lower)]

    metrics_matches = re.findall(
        r"(\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:k|m|b)?|\b\d+x\b|\d+\+?\s*(?:users|clients|requests|seconds|ms|hours))",
        lower,
    )

    word_count = len(text.split())
    if word_count < 250:
        length_feedback = "Under 250 words. Add project details and technical depth."
        length_score = 40
    elif 300 <= word_count <= 1100:
        length_feedback = "Optimal length for a 1 to 2 page ATS resume."
        length_score = 100
    elif 1100 < word_count <= 1600:
        length_feedback = "Slightly long. Trim older details unless applying for senior roles."
        length_score = 80
    else:
        length_feedback = "Over 1600 words. Condense content to reduce ATS noise."
        length_score = 60

    structural_score = int(
        (0.50 * section_health_pct)
        + (0.25 * length_score)
        + (0.25 * min(100, len(detected_verbs) * 10 + len(metrics_matches) * 15))
    )

    return {
        "sections": standard_sections,
        "sections_detected": detected_count,
        "total_sections": total_sections,
        "section_health_pct": section_health_pct,
        "action_verbs_found": detected_verbs,
        "metrics_found": metrics_matches[:5],
        "word_count": word_count,
        "length_feedback": length_feedback,
        "structural_score": structural_score,
    }


def extract_skills_from_text(text: str) -> Dict[str, List[str]]:
    """Extract domain-categorized skills using safe word-boundary matching."""
    lower = f" {clean_text(text)} "
    found_categorized: Dict[str, List[str]] = {}

    for category, skill_list in SKILL_TAXONOMY.items():
        found_in_cat = []
        for skill in skill_list:
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(skill) + r"(?![a-zA-Z0-9])"
            if re.search(pattern, lower):
                found_in_cat.append(skill)
        if found_in_cat:
            found_categorized[category] = sorted(found_in_cat)

    return found_categorized


def extract_tfidf_keywords(text: str, top_n: int = 25) -> List[Tuple[str, float]]:
    """Extract top unigrams and bigrams weighted by sublinear TF-IDF."""
    cleaned = clean_text(text)
    if not cleaned or len(cleaned.split()) < 3:
        return []

    try:
        tfidf = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_df=0.95,
            min_df=1,
            sublinear_tf=True,
        )
        vectors = tfidf.fit_transform([cleaned])
        scores = vectors.toarray()[0]
        feature_names = tfidf.get_feature_names_out()
        sorted_indices = np.argsort(scores)[::-1][:top_n]
        return [(str(feature_names[i]), float(scores[i])) for i in sorted_indices]
    except Exception:
        words = list({w for w in cleaned.split() if len(w) > 3})[:top_n]
        return [(w, 1.0) for w in words]


def compute_semantic_similarity(resume_text: str, jd_text: str) -> float:
    """Compute document similarity using SBERT embeddings if loaded, or TF-IDF cosine similarity."""
    cleaned_resume = clean_text(resume_text)
    cleaned_jd = clean_text(jd_text)

    if not cleaned_resume or not cleaned_jd:
        return 0.0

    if SBERT_ENABLED and embedder is not None:
        try:
            emb_resume = embedder.encode(cleaned_resume[:1500], convert_to_tensor=True)
            emb_jd = embedder.encode(cleaned_jd[:1500], convert_to_tensor=True)
            similarity = util.cos_sim(emb_resume, emb_jd).item()
            return max(0.0, min(1.0, float(similarity)))
        except Exception:
            pass

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform([cleaned_resume, cleaned_jd])
        sim_matrix = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
        return max(0.0, min(1.0, float(sim_matrix[0][0])))
    except Exception:
        return 0.0


def normalize_weights(weights: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Normalize custom scoring weights so they sum to 1.0."""
    defaults = {
        "skill_match": 0.40,
        "semantic_relevance": 0.35,
        "keyword_density": 0.15,
        "structural_health": 0.10,
    }
    if not weights:
        return defaults

    merged = {key: max(0.0, float(weights.get(key, defaults[key]))) for key in defaults}
    total = sum(merged.values())
    if total <= 0:
        return defaults
    return {key: val / total for key, val in merged.items()}


def calculate_ats_metrics(
    resume_text: str,
    jd_text: str,
    weights: Optional[Dict[str, float]] = None,
    semantic_threshold: float = 0.65,
) -> Dict[str, Any]:
    """Compute the full explainable ATS score, breakdowns, and improvement suggestions."""
    norm_weights = normalize_weights(weights)

    resume_skills_by_cat = extract_skills_from_text(resume_text)
    jd_skills_by_cat = extract_skills_from_text(jd_text)

    all_resume_skills = {skill for cat in resume_skills_by_cat.values() for skill in cat}
    all_jd_skills = {skill for cat in jd_skills_by_cat.values() for skill in cat}

    matched_skills = sorted(all_resume_skills & all_jd_skills)
    missing_skills = sorted(all_jd_skills - all_resume_skills)

    skills_breakdown_by_category: Dict[str, Dict[str, Any]] = {}
    for cat in SKILL_TAXONOMY:
        jd_cat_skills = set(jd_skills_by_cat.get(cat, []))
        resume_cat_skills = set(resume_skills_by_cat.get(cat, []))
        if jd_cat_skills or resume_cat_skills:
            matched_cat = sorted(jd_cat_skills & resume_cat_skills)
            missing_cat = sorted(jd_cat_skills - resume_cat_skills)
            skills_breakdown_by_category[cat] = {
                "jd_skills": sorted(jd_cat_skills),
                "resume_skills": sorted(resume_cat_skills),
                "matched": matched_cat,
                "missing": missing_cat,
                "match_rate": (len(matched_cat) / len(jd_cat_skills)) if jd_cat_skills else 1.0,
            }

    if all_jd_skills:
        skill_match_score = (len(matched_skills) / len(all_jd_skills)) * 100.0
    else:
        skill_match_score = 70.0

    jd_keywords_tuples = extract_tfidf_keywords(jd_text, top_n=25)
    jd_keyword_names = [kw for kw, _ in jd_keywords_tuples]
    cleaned_resume = clean_text(resume_text)

    matched_keywords: List[str] = []
    missing_keywords: List[str] = []
    for kw in jd_keyword_names:
        if re.search(r"\b" + re.escape(kw) + r"\b", cleaned_resume):
            matched_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    keyword_density_score = (
        (len(matched_keywords) / len(jd_keyword_names) * 100.0) if jd_keyword_names else 50.0
    )

    raw_similarity = compute_semantic_similarity(resume_text, jd_text)
    semantic_score = min(100.0, raw_similarity * 115.0)

    structure_audit = audit_resume_structure(resume_text)
    structure_score = structure_audit["structural_score"]

    total_score = (
        norm_weights["skill_match"] * skill_match_score
        + norm_weights["semantic_relevance"] * semantic_score
        + norm_weights["keyword_density"] * keyword_density_score
        + norm_weights["structural_health"] * structure_score
    )
    final_score = int(round(max(0.0, min(100.0, total_score))))

    if final_score >= 80:
        verdict = "Exceptional Match"
        verdict_color = "#60a5fa"
        verdict_message = "Strong alignment with the target role across required skills, phrasing, and structure."
    elif final_score >= 65:
        verdict = "Competitive Match"
        verdict_color = "#3b82f6"
        verdict_message = "Solid alignment with core requirements. Adding the remaining role keywords will improve ranking."
    elif final_score >= 50:
        verdict = "Moderate Match"
        verdict_color = "#334155"
        verdict_message = "Covers part of the role, though several required skills and phrases are missing."
    else:
        verdict = "Low Alignment"
        verdict_color = "#0b1120"
        verdict_message = "Substantial skill and keyword gaps remain between the resume and this job description."

    suggestions = generate_actionable_suggestions(
        missing_skills=missing_skills,
        matched_skills=matched_skills,
        structure_audit=structure_audit,
        final_score=final_score,
        missing_keywords=missing_keywords,
    )

    return {
        "ats_score": final_score,
        "score": final_score,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "verdict_message": verdict_message,
        "skill_match_score": round(skill_match_score, 1),
        "semantic_score": round(semantic_score, 1),
        "keyword_density_score": round(keyword_density_score, 1),
        "structure_score": round(structure_score, 1),
        "weights_used": {k: round(v, 3) for k, v in norm_weights.items()},
        "semantic_threshold": semantic_threshold,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "jd_keywords": jd_keyword_names,
        "skills_breakdown": skills_breakdown_by_category,
        "structure_audit": structure_audit,
        "suggestions": suggestions,
        "semantic_similarity_raw": round(raw_similarity, 3),
        "sbert_used": SBERT_ENABLED,
    }


def generate_actionable_suggestions(
    missing_skills: List[str],
    matched_skills: List[str],
    structure_audit: Dict[str, Any],
    final_score: int,
    missing_keywords: List[str],
) -> List[Dict[str, str]]:
    """Create prioritized, plain-language resume improvement recommendations."""
    suggestions: List[Dict[str, str]] = []

    if missing_skills:
        top_missing = missing_skills[:6]
        suggestions.append({
            "category": "Critical Skills Gap",
            "priority": "High",
            "icon": "skills",
            "title": f"Add missing core skills: {', '.join(top_missing)}",
            "advice": (
                f"The job description asks for {', '.join(top_missing)}. "
                "If you have hands-on experience with these tools, include them in your skills list and project bullets."
            ),
        })

    sections = structure_audit.get("sections", {})
    missing_sections = [name for name, present in sections.items() if not present]
    if missing_sections:
        suggestions.append({
            "category": "ATS Readability",
            "priority": "High",
            "icon": "structure",
            "title": f"Add standard section headers: {', '.join(missing_sections)}",
            "advice": (
                "ATS parsers look for explicit headings. Label sections clearly as "
                f"{', '.join(missing_sections)} so automated screeners classify your history accurately."
            ),
        })

    metrics = structure_audit.get("metrics_found", [])
    if len(metrics) < 2:
        suggestions.append({
            "category": "Impact & Metrics",
            "priority": "Medium",
            "icon": "metrics",
            "title": "Quantify achievements with numbers",
            "advice": (
                "Replace duty statements with measurable outcomes. For example, write "
                "'Built 12 FastAPI endpoints that cut p95 latency by 35% across 250k daily requests' "
                "instead of 'Responsible for API development'."
            ),
        })

    verbs = structure_audit.get("action_verbs_found", [])
    if len(verbs) < 5:
        suggestions.append({
            "category": "Language & Tone",
            "priority": "Medium",
            "icon": "verbs",
            "title": "Lead bullets with strong action verbs",
            "advice": (
                "Start experience bullets with concrete verbs such as Engineered, Architected, "
                "Optimized, Automated, or Delivered to clarify ownership."
            ),
        })

    if missing_keywords:
        top_kw = [kw for kw in missing_keywords if kw not in missing_skills][:5]
        if top_kw:
            suggestions.append({
                "category": "Keyword Optimization",
                "priority": "Low",
                "icon": "keywords",
                "title": f"Include role phrases naturally: {', '.join(top_kw)}",
                "advice": (
                    f"Reference terms such as {', '.join(top_kw)} inside relevant project descriptions "
                    "to improve phrase matching without repeating keywords mechanically."
                ),
            })

    if final_score >= 85 and not suggestions:
        suggestions.append({
            "category": "Optimization",
            "priority": "Info",
            "icon": "ready",
            "title": "Resume aligns well with this role",
            "advice": "Your skills, keywords, and section structure match the job description. Proofread before submitting.",
        })

    return suggestions


def generate_gemini_analysis(
    resume_text: str,
    jd_text: str,
    ats_results: Dict[str, Any],
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Google Gemini 2.5 Flash for recruiter feedback, bullet rewrites, and interview questions."""
    effective_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_key:
        return {
            "success": False,
            "error": "No Gemini API key provided. Enter your key in the settings panel or set GEMINI_API_KEY.",
        }

    prompt = f"""
You are a Tech Recruiter and ATS Specialist. Evaluate this resume against the job description.

JOB DESCRIPTION:
\"\"\"
{jd_text[:2000]}
\"\"\"

RESUME TEXT:
\"\"\"
{resume_text[:2000]}
\"\"\"

ATS SCORE COMPUTED: {ats_results.get('ats_score', 0)}%
MATCHED SKILLS: {', '.join(ats_results.get('matched_skills', []))}
MISSING SKILLS: {', '.join(ats_results.get('missing_skills', []))}

Return a JSON object with these keys:
1. "executive_summary": A 3-sentence recruiter assessment of candidate fit.
2. "tailored_bullet_rewrites": A list of 3 objects, each with "original_weak_phrase" and "improved_powerful_bullet" tailored to this job description.
3. "top_interview_questions": A list of 3 technical or behavioral interview questions based on the matched and missing skills.
4. "hiring_verdict": One of ["Strong Hire", "Potential Hire with Upskilling", "Do Not Interview"].
"""

    try:
        if GEMINI_ENABLED:
            client = genai.Client(api_key=effective_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            data = json.loads(response.text)
            return {"success": True, "data": data}

        import requests

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={effective_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"},
        }
        res = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=20)
        res.raise_for_status()
        raw_content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
        return {"success": True, "data": json.loads(raw_content)}
    except Exception as exc:
        return {"success": False, "error": f"Gemini API error: {exc}"}


def build_text_report(results: Dict[str, Any]) -> str:
    """Format a structured plain-text ATS audit report for export or download."""
    candidate = results.get("candidate_info", {})
    audit = results.get("structure_audit", {})
    matched = results.get("matched_skills", [])
    missing = results.get("missing_skills", [])
    suggestions = results.get("suggestions", [])

    lines = [
        "=" * 80,
        "HIRE-ARCHY ATS SCREENING & RESUME AUDIT REPORT",
        "=" * 80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Candidate Name: {candidate.get('candidate_name', 'Candidate')}",
        f"Email: {candidate.get('email') or 'N/A'}",
        f"Phone: {candidate.get('phone') or 'N/A'}",
        "",
        "-" * 80,
        f"OVERALL COMPATIBILITY SCORE: {results.get('ats_score', 0)}%",
        f"MATCH VERDICT: {results.get('verdict', 'N/A')}",
        "-" * 80,
        f"- Skills Match Rate:       {results.get('skill_match_score', 0)}%",
        f"- Semantic Relevance:      {results.get('semantic_score', 0)}%",
        f"- Keyword Context Density: {results.get('keyword_density_score', 0)}%",
        f"- Structural Health Score: {results.get('structure_score', 0)}%",
        "",
        "-" * 80,
        f"MATCHED COMPETENCIES ({len(matched)})",
        "-" * 80,
        ", ".join(matched) if matched else "None",
        "",
        "-" * 80,
        f"CRITICAL MISSING SKILLS ({len(missing)})",
        "-" * 80,
        ", ".join(missing) if missing else "None",
        "",
        "-" * 80,
        "ATS STRUCTURAL AUDIT",
        "-" * 80,
        f"Word Count: {audit.get('word_count', 0)} words ({audit.get('length_feedback', '')})",
        f"Standard Sections Found: {audit.get('sections_detected', 0)} / {audit.get('total_sections', 0)}",
        f"Action Verbs: {', '.join(audit.get('action_verbs_found', [])) or 'None'}",
        "",
        "-" * 80,
        "PRIORITIZED IMPROVEMENT SUGGESTIONS",
        "-" * 80,
    ]

    for idx, suggestion in enumerate(suggestions, start=1):
        lines.append(f"\n{idx}. [{suggestion.get('priority', 'Info')} Priority] {suggestion.get('title', '')}")
        lines.append(f"   Advice: {suggestion.get('advice', '')}")

    lines.extend(["", "=" * 80, "End of Report"])
    return "\n".join(lines)


SAMPLE_JOB_DESCRIPTIONS: Dict[str, str] = {
    "Full Stack Software Engineer": """Role: Full Stack Software Engineer (React / Python)
Location: Remote / Hybrid

About The Role:
We are hiring a Full Stack Engineer to build and maintain customer-facing web applications and backend services in an Agile product squad.

Key Responsibilities:
- Build responsive frontend interfaces using React, TypeScript, HTML5, and CSS3.
- Design and maintain backend APIs in Python (Django or FastAPI) backed by PostgreSQL.
- Write unit testing suites for critical workflows and review peer pull requests on GitHub.
- Package services with Docker and automate deployments via GitHub Actions CI/CD pipelines.
- Collaborate with designers and product managers in Agile and Scrum sprint cycles.

Requirements:
- 2+ years of software engineering experience with Python, JavaScript, and TypeScript.
- Practical experience with PostgreSQL, REST API design, and modern React components.
- Solid day-to-day workflow with Git, Linux environments, and automated testing.
""",
    "Machine Learning & AI Engineer": """Role: Machine Learning Engineer (Applied NLP & Python)
Department: Applied Intelligence Team

Overview:
We are looking for a Machine Learning Engineer to train, evaluate, and ship practical NLP and classification models into production workflows.

Responsibilities:
- Prepare structured and text datasets for training and evaluation using Python, Pandas, and NumPy.
- Train and fine-tune NLP and predictive models with PyTorch and Scikit-Learn.
- Define offline evaluation benchmarks and monitor model quality after release.
- Serve trained models as reliable endpoints using FastAPI and Docker.
- Partner with backend engineers to integrate inference services into product APIs.

Required Skills:
- Strong proficiency in Python, Scikit-Learn, and PyTorch.
- Practical grounding in NLP, feature engineering, and model evaluation.
- Experience with Git, Linux, and containerizing Python services with Docker.
""",
    "Cloud DevOps & SRE Engineer": """Role: DevOps & Site Reliability Engineer (AWS / Kubernetes)

Job Summary:
Join our platform engineering group to standardize cloud deployments, improve service reliability, and reduce manual operational toil.

Key Duties:
- Manage repeatable AWS cloud infrastructure using Terraform.
- Maintain containerized workloads running on Docker and Kubernetes.
- Improve build and release speed in CI/CD pipelines such as GitHub Actions.
- Set up actionable alerts and service dashboards using Prometheus and Grafana.
- Automate routine maintenance and incident diagnostics with Python or Bash scripting.

Qualifications:
- Hands-on production experience with AWS, Docker, Kubernetes, and Terraform.
- Solid Linux administration, networking, and cloud security fundamentals.
""",
    "Product Manager": """Role: Product Manager
Location: Hybrid

About The Role:
We are looking for a Product Manager to own product discovery, prioritize the roadmap, and guide engineering and design teams from concept to launch.

Key Responsibilities:
- Conduct customer discovery interviews and user research to uncover high-value pain points.
- Define clear product strategy, product roadmap priorities, and written requirements (PRDs and user stories).
- Lead sprint planning, backlog management, and Agile/Scrum ceremonies with engineering and design partners.
- Coordinate go-to-market product launch plans with marketing, sales, and customer success teams.
- Track core product metrics such as activation, retention, and conversion, and design A/B testing experiments to validate outcomes.

Qualifications:
- 2+ years of product management experience shipping B2B or consumer software products.
- Strong stakeholder management, leadership, and crisp presentation skills.
- Proven ability to make prioritization decisions from customer feedback and competitive analysis.
""",
}

SAMPLE_RESUME_TEXT = """
Alex Morgan
San Francisco, CA | (555) 382-9104 | alex.morgan.dev@email.com
linkedin.com/in/alexmorgandev | github.com/alexmorgandev

PROFESSIONAL SUMMARY
Results-driven Full Stack Software Engineer with 3+ years of experience designing and deploying scalable web applications, microservices, and cloud architectures. Proficient in Python, React, TypeScript, Docker, and AWS. Proven track record of improving application throughput by 40% and optimizing PostgreSQL database latency.

CORE COMPETENCIES & TECHNICAL SKILLS
- Programming Languages: Python, JavaScript, TypeScript, SQL, HTML5, CSS3, Bash
- Frameworks & Libraries: React, Node.js, FastAPI, Django, Redux, TailwindCSS, Express
- Databases: PostgreSQL, MongoDB, Redis, SQLite
- Cloud & DevOps: AWS (EC2, S3, RDS), Docker, Kubernetes, GitHub Actions, CI/CD, Linux, Git
- Methodologies: Agile, Scrum, RESTful APIs, Microservices, Unit Testing, System Design

PROFESSIONAL EXPERIENCE
Senior Software Engineer | CloudNova Solutions | 2022 - Present
- Architected and deployed 15+ production REST APIs using FastAPI and Python, handling over 500,000 daily requests.
- Engineered responsive React and TypeScript frontend components with Redux state management, improving user session time by 28%.
- Optimized complex PostgreSQL queries and implemented Redis caching, reducing average response latency from 450ms to 85ms.
- Containerized applications using Docker and established automated CI/CD deployment pipelines with GitHub Actions onto AWS EKS clusters.
- Spearheaded sprint planning and mentored 4 junior developers on clean code architecture and automated testing practices.

Software Developer | ByteCraft Interactive | 2020 - 2022
- Developed full-stack features using React, Node.js, and Express for an enterprise SaaS dashboard.
- Integrated third-party payment gateways and authentication using JWT and OAuth 2.0.
- Implemented comprehensive unit and integration test suites achieving 88% code coverage.
- Collaborated in cross-functional Agile squads with UX designers and product managers to ship 6 major product releases on schedule.

EDUCATION
Bachelor of Science in Computer Science
University of California, Berkeley | GPA: 3.8 / 4.0 | Graduated 2020

PROJECTS & CERTIFICATIONS
- Distributed Task Queue: Built a high-performance distributed task scheduler using Python, Redis, and WebSockets.
- AWS Certified Solutions Architect - Associate (2023)
"""


def run_ats(
    resume_input: Any,
    jd_text: str,
    semantic_threshold: float = 0.65,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Run the end-to-end ATS pipeline from raw text, file path, or file-like object."""
    if hasattr(resume_input, "read") or isinstance(resume_input, (bytes, io.BytesIO)):
        resume_text, metadata = extract_text_from_file(resume_input)
    elif isinstance(resume_input, str):
        if os.path.exists(resume_input) and os.path.isfile(resume_input):
            resume_text, metadata = extract_text_from_file(resume_input)
        else:
            resume_text = resume_input
            metadata = {
                "filename": "pasted_text.txt",
                "file_type": "txt",
                "word_count": len(resume_text.split()),
                "char_count": len(resume_text),
                "estimated_pages": 1,
            }
    else:
        resume_text = str(resume_input)
        metadata = {"filename": "unknown", "word_count": len(resume_text.split())}

    candidate_info = extract_candidate_metadata(resume_text)
    results = calculate_ats_metrics(
        resume_text=resume_text,
        jd_text=jd_text,
        weights=custom_weights,
        semantic_threshold=semantic_threshold,
    )
    results["metadata"] = metadata
    results["candidate_info"] = candidate_info
    results["resume_raw_text"] = resume_text
    results["jd_raw_text"] = jd_text
    return results
