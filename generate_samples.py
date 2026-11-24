"""
generate_samples.py
-------------------
Utility to generate presentation-ready sample resumes in PDF, DOCX, and TXT formats.
"""

import os
from fpdf import FPDF
import docx

def create_samples():
    output_dir = os.path.join(os.path.dirname(__file__), "sample_resumes")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Full Stack Resume Text
    fullstack_title = "Alex Morgan - Senior Full Stack Engineer"
    fullstack_contact = "San Francisco, CA | (555) 382-9104 | alex.morgan.dev@email.com | linkedin.com/in/alexmorgandev | github.com/alexmorgandev"
    fullstack_summary = (
        "Results-driven Full Stack Software Engineer with 4+ years of experience designing and deploying "
        "scalable web applications, microservices, and cloud architectures. Proficient in Python, React, TypeScript, "
        "PostgreSQL, Docker, and AWS. Proven track record of improving application throughput by 40% and optimizing "
        "database query latency."
    )
    fullstack_skills = (
        "Languages: Python, JavaScript, TypeScript, SQL, HTML5, CSS3, Bash\n"
        "Frameworks: React, Node.js, FastAPI, Django, Redux, TailwindCSS, Express\n"
        "Databases: PostgreSQL, MongoDB, Redis, SQLite\n"
        "Cloud & DevOps: AWS (EC2, S3, RDS), Docker, Kubernetes, GitHub Actions, CI/CD, Linux, Git\n"
        "Concepts: RESTful APIs, Microservices, Agile, Scrum, Unit Testing, System Design"
    )
    fullstack_exp = [
        ("Senior Full Stack Engineer | CloudNova Solutions (2022 - Present)", [
            "Architected and deployed 15+ production REST APIs using FastAPI and Python, handling over 500,000 daily requests.",
            "Engineered responsive React and TypeScript frontend components with Redux state management, improving user session time by 28%.",
            "Optimized complex PostgreSQL queries and implemented Redis caching, reducing average response latency from 450ms to 85ms.",
            "Containerized applications using Docker and established automated CI/CD deployment pipelines with GitHub Actions onto AWS EKS clusters.",
            "Spearheaded sprint planning and mentored 4 junior developers on clean code architecture and automated testing practices."
        ]),
        ("Software Developer | ByteCraft Interactive (2020 - 2022)", [
            "Developed full-stack features using React, Node.js, and Express for an enterprise SaaS dashboard.",
            "Integrated third-party payment gateways and secure authentication using JWT and OAuth 2.0.",
            "Implemented comprehensive unit and integration test suites achieving 88% code coverage with PyTest and Jest.",
            "Collaborated in cross-functional Agile squads with UX designers and product managers to ship 6 major product releases on schedule."
        ])
    ]
    fullstack_edu = "Bachelor of Science in Computer Science | University of California, Berkeley (GPA: 3.8 / 4.0)"
    fullstack_projects = (
        "Distributed Task Queue: Built a high-performance distributed task scheduler using Python, Redis, and WebSockets.\n"
        "AWS Certified Solutions Architect - Associate (2023)"
    )

    # 2. AI / ML Resume Text
    aiml_title = "Sarah Chen - Machine Learning & AI Engineer"
    aiml_contact = "Seattle, WA | (555) 729-4180 | sarah.chen.ai@email.com | linkedin.com/in/sarahchenai | github.com/sarahchenai"
    aiml_summary = (
        "Innovative Machine Learning Engineer with 3+ years of expertise in NLP, Large Language Models (LLMs), "
        "and Deep Learning. Strong proficiency in PyTorch, Transformers, Hugging Face, Scikit-Learn, and Python. "
        "Experienced in deploying high-throughput AI microservices on AWS and GCP using Docker and FastAPI."
    )
    aiml_skills = (
        "AI & NLP: PyTorch, TensorFlow, Transformers, Hugging Face, LangChain, RAG, BERT, Large Language Models, NLP\n"
        "Data Science: Scikit-Learn, Pandas, NumPy, SciPy, Matplotlib, Data Analysis, Data Visualization\n"
        "Backend & Cloud: Python, FastAPI, Docker, Kubernetes, AWS, GCP, RESTful APIs, Git, Linux, CI/CD"
    )
    aiml_exp = [
        ("Machine Learning Engineer | Apex AI Research (2022 - Present)", [
            "Developed and fine-tuned transformer models (BERT and LLaMA) using PyTorch and Hugging Face for automated document summarization.",
            "Built a Retrieval-Augmented Generation (RAG) pipeline with LangChain and vector databases, increasing search relevance by 35%.",
            "Preprocessed multi-gigabyte text datasets using Scikit-Learn, Pandas, and NumPy for NLP feature engineering.",
            "Containerized ML inference services using Docker and deployed on AWS with FastAPI, achieving 45ms average response time."
        ]),
        ("Data Scientist | DataVibe Analytics (2021 - 2022)", [
            "Trained predictive machine learning models with Scikit-Learn and XGBoost, improving churn forecasting accuracy by 22%.",
            "Created automated data visualization dashboards using Python, Matplotlib, and Seaborn for executive leadership.",
            "Collaborated with data engineers to build automated ETL pipelines on GCP."
        ])
    ]
    aiml_edu = "Master of Science in Artificial Intelligence | University of Washington | 2021"

    # --- Write DOCX Files ---
    def write_docx(filename, title, contact, summary, skills, experiences, education, extra=""):
        doc = docx.Document()
        doc.add_heading(title, 0)
        doc.add_paragraph(contact)
        
        doc.add_heading("Summary", level=1)
        doc.add_paragraph(summary)
        
        doc.add_heading("Skills", level=1)
        doc.add_paragraph(skills)
        
        doc.add_heading("Work Experience", level=1)
        for role_header, bullets in experiences:
            p = doc.add_paragraph()
            p.add_run(role_header).bold = True
            for b in bullets:
                doc.add_paragraph(b, style="List Bullet")
                
        doc.add_heading("Education", level=1)
        doc.add_paragraph(education)
        
        if extra:
            doc.add_heading("Projects & Certifications", level=1)
            doc.add_paragraph(extra)
            
        doc.save(os.path.join(output_dir, filename))

    write_docx("Alex_Morgan_FullStack.docx", fullstack_title, fullstack_contact, fullstack_summary, fullstack_skills, fullstack_exp, fullstack_edu, fullstack_projects)
    write_docx("Sarah_Chen_AIML.docx", aiml_title, aiml_contact, aiml_summary, aiml_skills, aiml_exp, aiml_edu)

    # --- Write PDF Files ---
    class PDFResume(FPDF):
        def header(self):
            pass
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(128, 128, 128)
            self.cell(180, 10, f"Page {self.page_no()}", align="C")

    def write_pdf(filename, title, contact, summary, skills, experiences, education, extra=""):
        pdf = PDFResume()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Header
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(180, 8, title)
        pdf.ln(8)
        
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(180, 6, contact)
        pdf.ln(7)

        def add_section(name):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(79, 70, 229)
            pdf.cell(180, 7, name.upper())
            pdf.ln(7)
            pdf.set_draw_color(226, 232, 240)
            pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 180, pdf.get_y())
            pdf.ln(3)

        # Summary
        add_section("Summary")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(180, 5, summary)
        pdf.ln(3)

        # Skills
        add_section("Technical Skills")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(180, 5, skills)
        pdf.ln(3)

        # Work Experience
        add_section("Work Experience")
        for role_header, bullets in experiences:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 41, 59)
            pdf.cell(180, 6, role_header)
            pdf.ln(6)
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(51, 65, 85)
            for b in bullets:
                pdf.multi_cell(180, 5, f"  * {b}")
            pdf.ln(2)

        # Education
        add_section("Education")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(180, 5, education)
        pdf.ln(3)

        if extra:
            add_section("Projects & Certifications")
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(180, 5, extra)

        pdf.output(os.path.join(output_dir, filename))

    write_pdf("Alex_Morgan_FullStack.pdf", fullstack_title, fullstack_contact, fullstack_summary, fullstack_skills, fullstack_exp, fullstack_edu, fullstack_projects)
    write_pdf("Sarah_Chen_AIML.pdf", aiml_title, aiml_contact, aiml_summary, aiml_skills, aiml_exp, aiml_edu)

    # --- Write Plain Text ---
    with open(os.path.join(output_dir, "Alex_Morgan_FullStack.txt"), "w", encoding="utf-8") as f:
        f.write(f"{fullstack_title}\n{fullstack_contact}\n\nSUMMARY\n{fullstack_summary}\n\nSKILLS\n{fullstack_skills}\n\nEXPERIENCE\n")
        for role_header, bullets in fullstack_exp:
            f.write(f"{role_header}\n")
            for b in bullets:
                f.write(f"- {b}\n")
        f.write(f"\nEDUCATION\n{fullstack_edu}\n\nPROJECTS\n{fullstack_projects}\n")

    print(f"Sample resumes generated successfully in: {output_dir}")

if __name__ == "__main__":
    create_samples()
