from django.urls import path

from ats import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/health", views.api_health, name="api_health"),
    path("api/samples", views.api_samples, name="api_samples"),
    path("api/demos/<str:demo_id>", views.api_demo, name="api_demo"),
    path("api/parse-resume", views.api_parse_resume, name="api_parse_resume"),
    path("api/analyze", views.api_analyze, name="api_analyze"),
    path("api/gemini-critique", views.api_gemini_critique, name="api_gemini_critique"),
    path("api/export-report", views.api_export_report, name="api_export_report"),
]
