"""
main.py
-------
Entrypoint facade for Hire-archy ATS Backend & Django WSGI application.
Re-exports all core ATS engine functions for backward compatibility with tests and scripts.
"""

from ats.engine import (
    ALL_ONTOLOGY_SKILLS,
    DOCX_ENABLED,
    GEMINI_ENABLED,
    PYPDF_ENABLED,
    SAMPLE_JOB_DESCRIPTIONS,
    SAMPLE_RESUME_TEXT,
    SBERT_ENABLED,
    SKILL_TAXONOMY,
    audit_resume_structure,
    build_text_report,
    calculate_ats_metrics,
    clean_text,
    compute_semantic_similarity,
    extract_candidate_metadata,
    extract_skills_from_text,
    extract_text_from_file,
    extract_tfidf_keywords,
    generate_actionable_suggestions,
    generate_gemini_analysis,
    normalize_weights,
    run_ats,
)
from hirearchy_site.wsgi import application

__all__ = [
    "application",
    "SKILL_TAXONOMY",
    "ALL_ONTOLOGY_SKILLS",
    "PYPDF_ENABLED",
    "DOCX_ENABLED",
    "SBERT_ENABLED",
    "GEMINI_ENABLED",
    "SAMPLE_JOB_DESCRIPTIONS",
    "SAMPLE_RESUME_TEXT",
    "extract_text_from_file",
    "clean_text",
    "extract_candidate_metadata",
    "audit_resume_structure",
    "extract_skills_from_text",
    "extract_tfidf_keywords",
    "compute_semantic_similarity",
    "normalize_weights",
    "calculate_ats_metrics",
    "generate_actionable_suggestions",
    "generate_gemini_analysis",
    "build_text_report",
    "run_ats",
]


if __name__ == "__main__":
    print("Testing Hire-archy ATS Backend Engine...")
    test_result = run_ats(SAMPLE_RESUME_TEXT, SAMPLE_JOB_DESCRIPTIONS["Full Stack Software Engineer"])
    print(f"ATS Score: {test_result['ats_score']}% ({test_result['verdict']})")
    print(f"Skill Match: {test_result['skill_match_score']}%")
    print(f"Matched Skills ({len(test_result['matched_skills'])}): {test_result['matched_skills']}")
    print(f"Missing Skills ({len(test_result['missing_skills'])}): {test_result['missing_skills']}")
    print(f"Structure Score: {test_result['structure_score']}%")
    print("Done! Backend is fully functional.")
