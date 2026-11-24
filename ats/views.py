"""
ats/views.py
------------
Django HTTP views serving the Hire-archy React frontend and REST API endpoints.
"""

import io
import json
import os
from pathlib import Path
from typing import Any, Dict

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ats.engine import (
    DOCX_ENABLED,
    GEMINI_ENABLED,
    PYPDF_ENABLED,
    SAMPLE_JOB_DESCRIPTIONS,
    SAMPLE_RESUME_TEXT,
    SBERT_ENABLED,
    SKILL_TAXONOMY,
    build_text_report,
    extract_candidate_metadata,
    extract_text_from_file,
    generate_gemini_analysis,
    run_ats,
)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


def _parse_json_body(request: HttpRequest) -> Dict[str, Any]:
    try:
        raw = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("JSON body must be an object.")
    return data


@require_GET
def index(request: HttpRequest) -> HttpResponse:
    """Serve the React frontend entrypoint."""
    index_path = Path(settings.BASE_DIR) / "frontend" / "index.html"
    if not index_path.exists():
        return JsonResponse({"detail": "Frontend index.html not found."}, status=404)
    return FileResponse(open(index_path, "rb"), content_type="text/html; charset=utf-8")


@require_GET
def api_health(request: HttpRequest) -> JsonResponse:
    """Return parser availability and NLP engine readiness."""
    return JsonResponse({
        "status": "ok",
        "backend": "django",
        "version": "2.0.0",
        "parsers": {
            "pypdf": PYPDF_ENABLED,
            "docx": DOCX_ENABLED,
        },
        "nlp": {
            "sbert": SBERT_ENABLED,
            "engine": "SBERT + TF-IDF" if SBERT_ENABLED else "TF-IDF Core",
        },
        "gemini": {
            "sdk_installed": GEMINI_ENABLED,
            "env_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
        },
    })


@require_GET
def api_samples(request: HttpRequest) -> JsonResponse:
    """Return available sample job descriptions, skill domains, and demo profiles."""
    return JsonResponse({
        "job_descriptions": SAMPLE_JOB_DESCRIPTIONS,
        "taxonomy_domains": list(SKILL_TAXONOMY.keys()),
        "demos": [
            {
                "id": "fullstack",
                "label": "Full Stack Demo",
                "candidate": "Alex Morgan",
                "role": "Full Stack Software Engineer",
            },
            {
                "id": "aiml",
                "label": "AI / ML Demo",
                "candidate": "Sarah Chen",
                "role": "Machine Learning & AI Engineer",
            },
        ],
    })


@require_GET
def api_demo(request: HttpRequest, demo_id: str) -> JsonResponse:
    """Load a prebuilt sample resume and job description pair with immediate ATS results."""
    samples_dir = Path(settings.BASE_DIR) / "sample_resumes"

    if demo_id == "fullstack":
        resume_text = SAMPLE_RESUME_TEXT.strip()
        jd_key = "Full Stack Software Engineer"
    elif demo_id == "aiml":
        aiml_docx = samples_dir / "Sarah_Chen_AIML.docx"
        if aiml_docx.exists():
            resume_text, _ = extract_text_from_file(str(aiml_docx))
        else:
            resume_text = SAMPLE_RESUME_TEXT.strip()
        jd_key = "Machine Learning & AI Engineer"
    else:
        return JsonResponse({"detail": f"Unknown demo preset '{demo_id}'."}, status=404)

    jd_text = SAMPLE_JOB_DESCRIPTIONS[jd_key]
    results = run_ats(resume_text, jd_text)
    return JsonResponse({
        "demo_id": demo_id,
        "jd_key": jd_key,
        "resume_text": resume_text,
        "jd_text": jd_text,
        "candidate_info": results["candidate_info"],
        "results": results,
    })


@csrf_exempt
@require_POST
def api_parse_resume(request: HttpRequest) -> JsonResponse:
    """Extract plain text, metadata, and candidate contact info from an uploaded PDF, DOCX, or TXT file."""
    uploaded = request.FILES.get("file")
    if uploaded is None:
        return JsonResponse({"detail": "No file was uploaded under field 'file'."}, status=400)

    filename = (uploaded.name or "resume.txt").strip()
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse(
            {"detail": f"Unsupported file format '{ext or 'unknown'}'. Upload a PDF, DOCX, or TXT file."},
            status=400,
        )

    raw_bytes = uploaded.read()
    if not raw_bytes:
        return JsonResponse({"detail": "Uploaded file is empty."}, status=400)
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        return JsonResponse({"detail": "Uploaded file exceeds the 10 MB size limit."}, status=413)

    try:
        extracted_text, metadata = extract_text_from_file(io.BytesIO(raw_bytes), filename_hint=filename)
    except Exception as exc:
        return JsonResponse({"detail": f"Failed to parse document: {exc}"}, status=422)

    if not extracted_text.strip():
        return JsonResponse(
            {"detail": "No readable text could be extracted from this file. Check if the PDF is scanned or empty."},
            status=422,
        )

    candidate_info = extract_candidate_metadata(extracted_text)
    return JsonResponse({
        "text": extracted_text,
        "metadata": metadata,
        "candidate_info": candidate_info,
    })


@csrf_exempt
@require_POST
def api_analyze(request: HttpRequest) -> JsonResponse:
    """Run the explainable ATS scoring pipeline against the provided resume and job description."""
    try:
        payload = _parse_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    resume_text = str(payload.get("resume_text") or "").strip()
    jd_text = str(payload.get("jd_text") or "").strip()
    if not resume_text:
        return JsonResponse({"detail": "Resume text cannot be empty."}, status=400)
    if not jd_text:
        return JsonResponse({"detail": "Job description text cannot be empty."}, status=400)

    try:
        semantic_threshold = float(payload.get("semantic_threshold", 0.65))
    except (TypeError, ValueError):
        return JsonResponse({"detail": "semantic_threshold must be numeric."}, status=400)
    semantic_threshold = max(0.1, min(0.99, semantic_threshold))

    weights = payload.get("weights")
    if weights is not None and not isinstance(weights, dict):
        return JsonResponse({"detail": "weights must be an object."}, status=400)

    results = run_ats(
        resume_input=resume_text,
        jd_text=jd_text,
        semantic_threshold=semantic_threshold,
        custom_weights=weights,
    )
    return JsonResponse(results)


@csrf_exempt
@require_POST
def api_gemini_critique(request: HttpRequest) -> JsonResponse:
    """Generate an executive AI evaluation, bullet rewrites, and interview questions via Gemini."""
    try:
        payload = _parse_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    resume_text = str(payload.get("resume_text") or "").strip()
    jd_text = str(payload.get("jd_text") or "").strip()
    ats_results = payload.get("ats_results") or {}
    api_key = payload.get("api_key")

    if not resume_text or not jd_text:
        return JsonResponse({"detail": "Both resume_text and jd_text are required."}, status=400)

    result = generate_gemini_analysis(
        resume_text=resume_text,
        jd_text=jd_text,
        ats_results=ats_results if isinstance(ats_results, dict) else {},
        api_key=api_key.strip() if isinstance(api_key, str) and api_key.strip() else None,
    )
    if not result.get("success"):
        return JsonResponse({"detail": result.get("error", "Gemini critique failed.")}, status=400)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def api_export_report(request: HttpRequest) -> HttpResponse:
    """Render a downloadable plain-text ATS audit report."""
    try:
        payload = _parse_json_body(request)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    ats_results = payload.get("ats_results")
    if not isinstance(ats_results, dict):
        return JsonResponse({"detail": "ats_results must be an object."}, status=400)

    report_text = build_text_report(ats_results)
    candidate_name = (
        ats_results.get("candidate_info", {}).get("candidate_name", "Candidate")
        or "Candidate"
    )
    safe_name = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in candidate_name.replace(" ", "_"))
    response = HttpResponse(report_text, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="ATS_Report_{safe_name}.txt"'
    return response
