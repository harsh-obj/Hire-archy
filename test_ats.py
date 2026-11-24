"""
test_ats.py
-----------
Automated test suite for Hire-archy ATS Backend & Django views.
Verifies parsing, scoring, recommendations, edge cases, and HTTP API routes.
"""

import json
import os
import sys
import unittest

import django

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hirearchy_site.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from main import (
    SAMPLE_JOB_DESCRIPTIONS,
    SAMPLE_RESUME_TEXT,
    audit_resume_structure,
    clean_text,
    extract_candidate_metadata,
    extract_skills_from_text,
    extract_text_from_file,
    run_ats,
)


class TestHireArchy(unittest.TestCase):
    def setUp(self):
        self.sample_resume = SAMPLE_RESUME_TEXT
        self.fullstack_jd = SAMPLE_JOB_DESCRIPTIONS["Full Stack Software Engineer"]
        self.aiml_jd = SAMPLE_JOB_DESCRIPTIONS["Machine Learning & AI Engineer"]
        self.samples_dir = os.path.join(PROJECT_DIR, "sample_resumes")
        self.client = Client()

    def test_clean_text_preserves_special_tech(self):
        """Verify that tech tokens like C++, C#, .NET, and node.js are preserved."""
        text = "Skilled in C++, C#, .NET, and Node.js with Vue.js!"
        cleaned = clean_text(text)
        self.assertIn("c++", cleaned)
        self.assertIn("c#", cleaned)
        self.assertIn(".net", cleaned)
        self.assertIn("node.js", cleaned)
        self.assertIn("vue.js", cleaned)

    def test_extract_candidate_metadata(self):
        """Verify regex extraction of candidate email, phone, links, and name."""
        meta = extract_candidate_metadata(self.sample_resume)
        self.assertEqual(meta["email"], "alex.morgan.dev@email.com")
        self.assertIn("555", meta["phone"])
        self.assertIn("linkedin.com", meta["linkedin"])
        self.assertIn("github.com", meta["github"])
        self.assertIn("Alex", meta["candidate_name"])

    def test_extract_pdf_file(self):
        """Test extraction from a real PDF resume."""
        pdf_path = os.path.join(self.samples_dir, "Alex_Morgan_FullStack.pdf")
        if os.path.exists(pdf_path):
            text, meta = extract_text_from_file(pdf_path)
            self.assertEqual(meta["file_type"], "pdf")
            self.assertGreater(meta["word_count"], 150)
            self.assertIn("Alex Morgan", text)
            self.assertIn("Python", text)

    def test_extract_docx_file(self):
        """Test extraction from a real DOCX resume."""
        docx_path = os.path.join(self.samples_dir, "Sarah_Chen_AIML.docx")
        if os.path.exists(docx_path):
            text, meta = extract_text_from_file(docx_path)
            self.assertEqual(meta["file_type"], "docx")
            self.assertGreater(meta["word_count"], 150)
            self.assertIn("Sarah Chen", text)
            self.assertIn("PyTorch", text)

    def test_skill_extraction(self):
        """Verify skills are extracted into proper taxonomy categories."""
        text = "Expert in Python, React, AWS, Docker, Kubernetes, and PostgreSQL."
        skills = extract_skills_from_text(text)
        self.assertIn("Languages", skills)
        self.assertIn("python", skills["Languages"])
        self.assertIn("Frameworks & Libraries", skills)
        self.assertIn("react", skills["Frameworks & Libraries"])
        self.assertIn("Cloud & DevOps", skills)
        self.assertIn("docker", skills["Cloud & DevOps"])
        self.assertIn("Databases & Storage", skills)
        self.assertIn("postgresql", skills["Databases & Storage"])

    def test_structure_audit(self):
        """Verify section detection and length audit."""
        audit = audit_resume_structure(self.sample_resume)
        self.assertTrue(audit["sections"]["Work Experience"])
        self.assertTrue(audit["sections"]["Education"])
        self.assertTrue(audit["sections"]["Skills"])
        self.assertTrue(audit["sections"]["Projects"])
        self.assertGreaterEqual(audit["section_health_pct"], 60)
        self.assertGreater(len(audit["action_verbs_found"]), 0)

    def test_run_ats_score_range_and_output(self):
        """Verify end-to-end ATS score computation produces valid ranges and keys."""
        results = run_ats(self.sample_resume, self.fullstack_jd)
        self.assertIn("ats_score", results)
        self.assertIn("score", results)
        self.assertIn("verdict", results)
        self.assertIn("matched_skills", results)
        self.assertIn("missing_skills", results)
        self.assertIn("suggestions", results)
        self.assertIn("structure_audit", results)
        self.assertGreaterEqual(results["ats_score"], 50)
        self.assertLessEqual(results["ats_score"], 100)
        self.assertGreater(len(results["matched_skills"]), 5)

    def test_low_match_scenario(self):
        """Verify that an unrelated resume gets a lower score with proper suggestions."""
        unrelated_resume = """
        John Smith - Elementary School Teacher
        Experienced teacher with 5 years experience in lesson planning, classroom management,
        parent communication, grading assignments, and organizing school field trips.
        Education: Bachelor of Arts in Education.
        """
        results = run_ats(unrelated_resume, self.fullstack_jd)
        self.assertLess(results["ats_score"], 50)
        self.assertEqual(results["verdict"], "Low Alignment")
        self.assertGreater(len(results["missing_skills"]), 5)
        self.assertGreater(len(results["suggestions"]), 0)

    def test_realistic_product_manager_jd(self):
        """Verify Product Manager JD reflects real-world PM skills without SQL/engineering bloat."""
        pm_jd = SAMPLE_JOB_DESCRIPTIONS["Product Manager"]
        self.assertNotIn("sql", pm_jd.lower())
        pm_skills = extract_skills_from_text(pm_jd)
        self.assertIn("Product & Strategy", pm_skills)
        self.assertIn("product roadmap", pm_skills["Product & Strategy"])
        self.assertIn("user research", pm_skills["Product & Strategy"])

        pm_resume = """
        Priya Nair
        Bangalore | (555) 412-9088 | priya.nair@email.com
        linkedin.com/in/priyanairpm

        SUMMARY
        Product Manager with 4 years of experience leading customer discovery, user research,
        product roadmap prioritization, and agile sprints across SaaS web and mobile products.
        Focused on customer outcomes, clear product requirements, and measurable adoption.

        CORE SKILLS
        Product Strategy, Product Roadmap, Customer Discovery, User Research, Backlog Management,
        User Stories, Sprint Planning, Go-To-Market, Product Launch, A/B Testing, Product Metrics,
        Competitive Analysis, Stakeholder Management, Agile, Scrum, Leadership, Presentation, Communication

        WORK EXPERIENCE
        Product Manager | Nimbus Apps | 2022 - Present
        - Led customer discovery interviews and user research with 65 enterprise customers to identify top workflow bottlenecks.
        - Owned product strategy, backlog management, user stories, and agile sprint planning for a 12-person product squad.
        - Coordinated go-to-market product launch campaigns with marketing and sales, lifting new user activation by 24%.
        - Designed A/B testing experiments and tracked product metrics including retention and conversion, improving 90-day retention by 18%.
        - Managed executive stakeholder alignment through quarterly product roadmap reviews and competitive analysis.

        Associate Product Manager | BrightLane Software | 2020 - 2022
        - Partnered with UX designers to run usability testing sessions and refine onboarding wireframes, reducing drop-off by 15%.
        - Groomed Scrum backlogs, wrote clear PRDs, and prioritized features based on customer feedback and business impact.
        - Supported 4 major product launches and presented quarterly release outcomes to leadership.

        EDUCATION
        Master of Business Administration (MBA) in Product Management
        Bachelor of Arts in Economics

        CERTIFICATIONS
        Certified Scrum Product Owner (CSPO)
        """
        res = run_ats(pm_resume, pm_jd)
        self.assertGreaterEqual(res["ats_score"], 60)
        self.assertNotIn("sql", res["missing_skills"])

    def test_django_health_and_samples(self):
        """Verify Django /api/health and /api/samples endpoints."""
        health_res = self.client.get("/api/health")
        self.assertEqual(health_res.status_code, 200)
        health_json = health_res.json()
        self.assertEqual(health_json["status"], "ok")
        self.assertEqual(health_json["backend"], "django")

        samples_res = self.client.get("/api/samples")
        self.assertEqual(samples_res.status_code, 200)
        samples_json = samples_res.json()
        self.assertIn("Full Stack Software Engineer", samples_json["job_descriptions"])

    def test_django_analyze_and_export(self):
        """Verify Django /api/analyze and /api/export-report endpoints."""
        res = self.client.post(
            "/api/analyze",
            data=json.dumps({
                "resume_text": self.sample_resume,
                "jd_text": self.fullstack_jd,
                "semantic_threshold": 0.65,
            }),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ats_score", data)
        self.assertGreaterEqual(data["ats_score"], 50)

        export_res = self.client.post(
            "/api/export-report",
            data=json.dumps({"ats_results": data}),
            content_type="application/json",
        )
        self.assertEqual(export_res.status_code, 200)
        self.assertIn("HIRE-ARCHY ATS SCREENING & RESUME AUDIT REPORT", export_res.content.decode("utf-8"))

    def test_django_parse_upload_demos_and_index(self):
        """Verify Django /api/parse-resume, /api/demos/<id>, and root HTML serving."""
        pdf_path = os.path.join(self.samples_dir, "Alex_Morgan_FullStack.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as handle:
                upload = SimpleUploadedFile(
                    "Alex_Morgan_FullStack.pdf",
                    handle.read(),
                    content_type="application/pdf",
                )
            upload_res = self.client.post("/api/parse-resume", {"file": upload})
            self.assertEqual(upload_res.status_code, 200)
            upload_json = upload_res.json()
            self.assertIn("Python", upload_json["text"])
            self.assertEqual(upload_json["metadata"]["file_type"], "pdf")

        demo_res = self.client.get("/api/demos/aiml")
        self.assertEqual(demo_res.status_code, 200)
        self.assertIn("results", demo_res.json())

        index_res = self.client.get("/")
        self.assertEqual(index_res.status_code, 200)
        index_html = b"".join(index_res.streaming_content).decode("utf-8")
        self.assertIn("Hire-archy", index_html)

    def test_custom_runserver_port_discovery_and_lan(self):
        """Verify custom runserver defaults to 0.0.0.0 and discovers available ports."""
        from ats.management.commands.runserver import (
            Command as RunserverCommand,
            find_available_ports,
            get_lan_ips,
        )

        self.assertEqual(RunserverCommand.default_addr, "0.0.0.0")
        ports = find_available_ports("0.0.0.0", 8080)
        self.assertIsInstance(ports, list)
        self.assertGreater(len(ports), 0)
        self.assertIsInstance(get_lan_ips(), list)


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING HIRE-ARCHY ATS TEST SUITE")
    print("=" * 60)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHireArchy)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if result.wasSuccessful():
        print("\nAll test suites passed with 100% success!")
        sys.exit(0)
    else:
        print("\nSome tests failed!")
        sys.exit(1)
