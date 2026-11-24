const { useEffect, useMemo, useRef, useState } = React;

const DEFAULT_WEIGHTS = {
  skill_match: 0.40,
  semantic_relevance: 0.35,
  keyword_density: 0.15,
  structural_health: 0.10,
};

const TABS = [
  { id: "skills", label: "Skill gaps" },
  { id: "charts", label: "Visual charts" },
  { id: "audit", label: "Readability audit" },
  { id: "advice", label: "Recommendations" },
  { id: "gemini", label: "AI critique" },
  { id: "export", label: "Export report" },
];

function countWords(text) {
  if (!text || !text.trim()) return 0;
  return text.trim().split(/\s+/).length;
}

function titleCaseSkill(value) {
  return value.replace(/\b\w/g, (ch) => ch.toUpperCase());
}

function formatClientReport(results) {
  if (!results) return "";
  const candidate = results.candidate_info || {};
  const audit = results.structure_audit || {};
  const matched = results.matched_skills || [];
  const missing = results.missing_skills || [];
  const suggestions = results.suggestions || [];

  const lines = [
    "================================================================================",
    "HIRE-ARCHY ATS SCREENING & RESUME AUDIT REPORT",
    "================================================================================",
    `Candidate Name: ${candidate.candidate_name || "Candidate"}`,
    `Email: ${candidate.email || "N/A"}`,
    `Phone: ${candidate.phone || "N/A"}`,
    "",
    "--------------------------------------------------------------------------------",
    `OVERALL COMPATIBILITY SCORE: ${results.ats_score}%`,
    `MATCH VERDICT: ${results.verdict}`,
    "--------------------------------------------------------------------------------",
    `- Skills Match Rate:       ${results.skill_match_score}%`,
    `- Semantic Relevance:      ${results.semantic_score}%`,
    `- Keyword Context Density: ${results.keyword_density_score}%`,
    `- Structural Health Score: ${results.structure_score}%`,
    "",
    "--------------------------------------------------------------------------------",
    `MATCHED COMPETENCIES (${matched.length})`,
    "--------------------------------------------------------------------------------",
    matched.length ? matched.join(", ") : "None",
    "",
    "--------------------------------------------------------------------------------",
    `CRITICAL MISSING SKILLS (${missing.length})`,
    "--------------------------------------------------------------------------------",
    missing.length ? missing.join(", ") : "None",
    "",
    "--------------------------------------------------------------------------------",
    "ATS STRUCTURAL AUDIT",
    "--------------------------------------------------------------------------------",
    `Word Count: ${audit.word_count || 0} words (${audit.length_feedback || ""})`,
    `Standard Sections Found: ${audit.sections_detected || 0} / ${audit.total_sections || 0}`,
    `Action Verbs: ${(audit.action_verbs_found || []).join(", ") || "None"}`,
    "",
    "--------------------------------------------------------------------------------",
    "PRIORITIZED IMPROVEMENT SUGGESTIONS",
    "--------------------------------------------------------------------------------",
  ];

  suggestions.forEach((s, idx) => {
    lines.push(`\n${idx + 1}. [${s.priority} Priority] ${s.title}`);
    lines.push(`   Advice: ${s.advice}`);
  });

  lines.push("", "================================================================================", "End of Report");
  return lines.join("\n");
}

function ScoreRing({ score }) {
  const radius = 66;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, Number(score) || 0));
  const dashOffset = circumference - (clamped / 100) * circumference;

  return (
    <svg className="gauge-svg" viewBox="0 0 168 168" role="img" aria-label={`ATS score ${clamped} percent`}>
      <circle
        cx="84"
        cy="84"
        r={radius}
        fill="none"
        stroke="#1e293b"
        strokeWidth="12"
      />
      <circle
        cx="84"
        cy="84"
        r={radius}
        fill="none"
        stroke="#60a5fa"
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform="rotate(-90 84 84)"
        style={{ transition: "stroke-dashoffset 0.45s ease" }}
      />
      <text
        x="84"
        y="80"
        textAnchor="middle"
        fill="#ffffff"
        fontSize="36"
        fontWeight="700"
        fontFamily="IBM Plex Mono, monospace"
      >
        {clamped}%
      </text>
      <text
        x="84"
        y="104"
        textAnchor="middle"
        fill="#93c5fd"
        fontSize="12"
        fontWeight="600"
      >
        ATS match
      </text>
    </svg>
  );
}

function CompetencyRadar({ breakdown }) {
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const categories = Object.keys(breakdown || {});

  if (categories.length < 3) {
    return (
      <p className="helper-text">
        At least three active skill domains are needed to plot the competency radar.
      </p>
    );
  }

  const size = 440;
  const cx = size / 2;
  const cy = size / 2;
  const maxR = 114;

  const jdCounts = categories.map((c) => (breakdown[c].jd_skills || []).length);
  const matchedCounts = categories.map((c) => (breakdown[c].matched || []).length);
  const maxVal = Math.max(1, ...jdCounts, ...matchedCounts);

  const pointAt = (index, value) => {
    const angle = (Math.PI * 2 * index) / categories.length - Math.PI / 2;
    const ratio = value / maxVal;
    return {
      x: cx + Math.cos(angle) * maxR * ratio,
      y: cy + Math.sin(angle) * maxR * ratio,
    };
  };

  const labelAt = (index) => {
    const angle = (Math.PI * 2 * index) / categories.length - Math.PI / 2;
    return {
      x: cx + Math.cos(angle) * (maxR + 22),
      y: cy + Math.sin(angle) * (maxR + 22),
    };
  };

  const toPointsAttr = (values) =>
    values.map((val, idx) => {
      const pt = pointAt(idx, val);
      return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
    }).join(" ");

  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <div className="chart-container">
      <div className="chart-legend">
        <span className="legend-item">
          <span className="legend-swatch blue"></span>
          Candidate matched skills
        </span>
        <span className="legend-item">
          <span className="legend-swatch black"></span>
          Job requirement
        </span>
      </div>

      <svg className="radar-svg" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Competency radar chart">
        {rings.map((ring) => (
          <polygon
            key={ring}
            points={categories.map((_, idx) => {
              const pt = pointAt(idx, maxVal * ring);
              return `${pt.x.toFixed(1)},${pt.y.toFixed(1)}`;
            }).join(" ")}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth="1"
          />
        ))}

        {categories.map((cat, idx) => {
          const outer = pointAt(idx, maxVal);
          const lbl = labelAt(idx);
          const shortName = cat.split(" & ")[0].split(" ")[0];
          const anchor = lbl.x < cx - 12 ? "end" : lbl.x > cx + 12 ? "start" : "middle";

          return (
            <g key={cat}>
              <line x1={cx} y1={cy} x2={outer.x} y2={outer.y} stroke="#cbd5e1" strokeWidth="1" />
              <text
                x={lbl.x}
                y={lbl.y}
                textAnchor={anchor}
                dominantBaseline="middle"
                fill="#0a0f1a"
                fontSize="12"
                fontWeight="600"
              >
                {shortName}
              </text>
            </g>
          );
        })}

        <polygon
          points={toPointsAttr(jdCounts)}
          fill="rgba(10, 15, 26, 0.06)"
          stroke="#0a0f1a"
          strokeWidth="2"
          strokeDasharray="5 4"
        />

        <polygon
          points={toPointsAttr(matchedCounts)}
          fill="rgba(59, 130, 246, 0.20)"
          stroke="#3b82f6"
          strokeWidth="2.5"
        />

        {categories.map((cat, idx) => {
          const pt = pointAt(idx, matchedCounts[idx]);
          return (
            <circle
              key={`pt-${cat}`}
              cx={pt.x}
              cy={pt.y}
              r={hoveredIdx === idx ? 7 : 5}
              fill="#3b82f6"
              stroke="#ffffff"
              strokeWidth="2"
              style={{ cursor: "pointer" }}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            />
          );
        })}
      </svg>

      {hoveredIdx !== null && categories[hoveredIdx] ? (
        <div className="file-meta-bar">
          <strong>{categories[hoveredIdx]}</strong>
          <span>
            Matched {matchedCounts[hoveredIdx]} of {jdCounts[hoveredIdx]} required skills
          </span>
        </div>
      ) : (
        <p className="helper-text">Hover a blue data point to inspect exact counts for that domain.</p>
      )}
    </div>
  );
}

function App() {
  const [health, setHealth] = useState(null);
  const [sampleJDs, setSampleJDs] = useState({});
  const [selectedSampleJD, setSelectedSampleJD] = useState("custom");

  const [resumeInputMode, setResumeInputMode] = useState("upload");
  const [resumeText, setResumeText] = useState("");
  const [jdText, setJdText] = useState("");
  const [uploadedMeta, setUploadedMeta] = useState(null);
  const [candidateInfo, setCandidateInfo] = useState(null);

  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [semanticThreshold, setSemanticThreshold] = useState(0.65);
  const [apiKey, setApiKey] = useState("");
  const [settingsOpen, setSettingsOpen] = useState(false);

  const [results, setResults] = useState(null);
  const [activeTab, setActiveTab] = useState("skills");
  const [geminiCritique, setGeminiCritique] = useState(null);

  const [isParsing, setIsParsing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isGeneratingAI, setIsGeneratingAI] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [copiedReport, setCopiedReport] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const fileInputRef = useRef(null);
  const resultsRef = useRef(null);

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((data) => setHealth(data))
      .catch(() => setHealth({ status: "offline" }));

    fetch("/api/samples")
      .then((res) => res.json())
      .then((data) => setSampleJDs(data.job_descriptions || {}))
      .catch(() => {});
  }, []);

  const normalizedWeights = useMemo(() => {
    const total =
      weights.skill_match +
      weights.semantic_relevance +
      weights.keyword_density +
      weights.structural_health;
    if (total <= 0) return DEFAULT_WEIGHTS;
    return {
      skill_match: weights.skill_match / total,
      semantic_relevance: weights.semantic_relevance / total,
      keyword_density: weights.keyword_density / total,
      structural_health: weights.structural_health / total,
    };
  }, [weights]);

  const reportText = useMemo(() => formatClientReport(results), [results]);

  async function handleFileUpload(file) {
    if (!file) return;
    setErrorMsg("");
    setIsParsing(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch("/api/parse-resume", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Could not extract text from the uploaded file.");
      }
      setResumeText(data.text || "");
      setUploadedMeta(data.metadata || null);
      setCandidateInfo(data.candidate_info || null);
      setResults(null);
      setGeminiCritique(null);
    } catch (err) {
      setErrorMsg(err.message || "File parsing failed.");
    } finally {
      setIsParsing(false);
    }
  }

  async function handleLoadDemo(demoId) {
    setErrorMsg("");
    setIsAnalyzing(true);
    try {
      const res = await fetch(`/api/demos/${demoId}`);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Unable to load demo preset.");
      }
      setResumeText(data.resume_text || "");
      setJdText(data.jd_text || "");
      setSelectedSampleJD(data.jd_key || "custom");
      setUploadedMeta(null);
      setCandidateInfo(data.candidate_info || null);
      setResults(data.results || null);
      setGeminiCritique(null);
      setActiveTab("skills");
      setResumeInputMode("paste");
    } catch (err) {
      setErrorMsg(err.message || "Failed to load demo data.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleAnalyze() {
    setErrorMsg("");
    if (!resumeText.trim()) {
      setErrorMsg("Upload a resume file or paste resume text before running analysis.");
      return;
    }
    if (!jdText.trim()) {
      setErrorMsg("Select a sample role or paste a target job description before running analysis.");
      return;
    }

    setIsAnalyzing(true);
    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          jd_text: jdText,
          semantic_threshold: semanticThreshold,
          weights: normalizedWeights,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "ATS evaluation failed.");
      }
      setResults(data);
      setCandidateInfo(data.candidate_info || null);
      setGeminiCritique(null);
      setTimeout(() => {
        if (resultsRef.current) {
          resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }, 60);
    } catch (err) {
      setErrorMsg(err.message || "Could not complete ATS evaluation.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleGenerateGemini() {
    if (!results) return;
    setErrorMsg("");
    setIsGeneratingAI(true);
    try {
      const res = await fetch("/api/gemini-critique", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          jd_text: jdText,
          ats_results: results,
          api_key: apiKey.trim() || null,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Gemini critique request failed.");
      }
      setGeminiCritique(data.data);
    } catch (err) {
      setErrorMsg(err.message || "Gemini AI request failed.");
    } finally {
      setIsGeneratingAI(false);
    }
  }

  async function handleDownloadReport() {
    if (!results) return;
    try {
      const res = await fetch("/api/export-report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ats_results: results }),
      });
      if (!res.ok) throw new Error("Export failed.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      const rawName = (results.candidate_info && results.candidate_info.candidate_name) || "Candidate";
      anchor.href = url;
      anchor.download = `ATS_Report_${rawName.replace(/\s+/g, "_")}.txt`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setErrorMsg(err.message || "Unable to download report.");
    }
  }

  function handleCopyReport() {
    if (!reportText) return;
    navigator.clipboard.writeText(reportText).then(() => {
      setCopiedReport(true);
      setTimeout(() => setCopiedReport(false), 2000);
    });
  }

  function handleReset() {
    setResumeText("");
    setJdText("");
    setSelectedSampleJD("custom");
    setUploadedMeta(null);
    setCandidateInfo(null);
    setResults(null);
    setGeminiCritique(null);
    setErrorMsg("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }

  function handleSampleChange(event) {
    const key = event.target.value;
    setSelectedSampleJD(key);
    if (key !== "custom" && sampleJDs[key]) {
      setJdText(sampleJDs[key]);
    }
  }

  const verdictTone =
    results && results.verdict === "Moderate Match"
      ? "moderate"
      : results && results.verdict === "Low Alignment"
      ? "low"
      : "";

  const effectiveGeminiAvailable = Boolean(
    apiKey.trim() || (health && health.gemini && health.gemini.env_key_configured)
  );

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="container topbar-inner">
          <div className="brand">
            <div className="brand-mark" aria-hidden="true">H</div>
            <div>
              <h1 className="brand-title">Hire-archy</h1>
              <p className="brand-sub">Python Django ATS screening and resume audit</p>
            </div>
          </div>

          <div className="topbar-actions">
            <span className="status-pill" title="Backend NLP engine status">
              <span className={`status-dot ${health && health.status === "ok" ? "" : "offline"}`}></span>
              {health && health.nlp ? health.nlp.engine : "Connecting"}
            </span>
            <button type="button" className="nav-btn" onClick={() => handleLoadDemo("fullstack")}>
              Full Stack demo
            </button>
            <button type="button" className="nav-btn" onClick={() => handleLoadDemo("aiml")}>
              AI / ML demo
            </button>
            <button
              type="button"
              className={`nav-btn ${settingsOpen ? "nav-btn-active" : ""}`}
              onClick={() => setSettingsOpen((prev) => !prev)}
              aria-expanded={settingsOpen}
            >
              Scoring &amp; AI settings
            </button>
            <button type="button" className="nav-btn" onClick={handleReset}>
              Clear inputs
            </button>
          </div>
        </div>
      </header>

      {settingsOpen && (
        <section className="settings-drawer" aria-label="Scoring weights and API configuration">
          <div className="container settings-grid">
            <div className="drawer-card">
              <h2 className="drawer-heading">Composite score weights</h2>
              <div className="slider-row">
                <label htmlFor="w-skills">Skill match</label>
                <input
                  id="w-skills"
                  type="range"
                  min="0.1"
                  max="0.7"
                  step="0.05"
                  value={weights.skill_match}
                  onChange={(e) => setWeights({ ...weights, skill_match: parseFloat(e.target.value) })}
                />
                <span className="mono-val">{Math.round(normalizedWeights.skill_match * 100)}%</span>
              </div>
              <div className="slider-row">
                <label htmlFor="w-sem">Semantic relevance</label>
                <input
                  id="w-sem"
                  type="range"
                  min="0.1"
                  max="0.6"
                  step="0.05"
                  value={weights.semantic_relevance}
                  onChange={(e) => setWeights({ ...weights, semantic_relevance: parseFloat(e.target.value) })}
                />
                <span className="mono-val">{Math.round(normalizedWeights.semantic_relevance * 100)}%</span>
              </div>
              <div className="slider-row">
                <label htmlFor="w-kw">Keyword context</label>
                <input
                  id="w-kw"
                  type="range"
                  min="0.05"
                  max="0.4"
                  step="0.05"
                  value={weights.keyword_density}
                  onChange={(e) => setWeights({ ...weights, keyword_density: parseFloat(e.target.value) })}
                />
                <span className="mono-val">{Math.round(normalizedWeights.keyword_density * 100)}%</span>
              </div>
              <div className="slider-row">
                <label htmlFor="w-str">Structure health</label>
                <input
                  id="w-str"
                  type="range"
                  min="0.05"
                  max="0.3"
                  step="0.05"
                  value={weights.structural_health}
                  onChange={(e) => setWeights({ ...weights, structural_health: parseFloat(e.target.value) })}
                />
                <span className="mono-val">{Math.round(normalizedWeights.structural_health * 100)}%</span>
              </div>
              <div className="slider-row">
                <label htmlFor="sem-threshold">Semantic threshold</label>
                <input
                  id="sem-threshold"
                  type="range"
                  min="0.5"
                  max="0.9"
                  step="0.01"
                  value={semanticThreshold}
                  onChange={(e) => setSemanticThreshold(parseFloat(e.target.value))}
                />
                <span className="mono-val">{semanticThreshold.toFixed(2)}</span>
              </div>
            </div>

            <div className="drawer-card">
              <h2 className="drawer-heading">Optional Gemini API key</h2>
              <label className="field-label" htmlFor="gemini-key-input">
                Google Gemini API key
              </label>
              <input
                id="gemini-key-input"
                type="password"
                className="text-input"
                placeholder="Paste key from Google AI Studio"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <p className="helper-text">
                Core scoring runs offline with Python and scikit-learn. Add a Gemini key only if you want generative bullet rewrites and interview questions.
              </p>
            </div>

            <div className="drawer-card">
              <h2 className="drawer-heading">Backend capabilities</h2>
              <ul className="diag-list">
                <li className="diag-item">
                  <span>PDF parser (pypdf)</span>
                  <span className={`diag-badge ${health?.parsers?.pypdf ? "" : "muted"}`}>
                    {health?.parsers?.pypdf ? "Ready" : "Unavailable"}
                  </span>
                </li>
                <li className="diag-item">
                  <span>DOCX parser (python-docx)</span>
                  <span className={`diag-badge ${health?.parsers?.docx ? "" : "muted"}`}>
                    {health?.parsers?.docx ? "Ready" : "Unavailable"}
                  </span>
                </li>
                <li className="diag-item">
                  <span>Similarity model</span>
                  <span className="diag-badge">
                    {health?.nlp?.sbert ? "SBERT" : "TF-IDF"}
                  </span>
                </li>
                <li className="diag-item">
                  <span>Gemini client</span>
                  <span className={`diag-badge ${health?.gemini?.sdk_installed ? "" : "muted"}`}>
                    {health?.gemini?.sdk_installed ? "SDK ready" : "HTTP fallback"}
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </section>
      )}

      <main className="main-content">
        <div className="container">
          <div className="page-intro">
            <h2 className="page-title">Screen a resume against a job description</h2>
            <p className="page-subtitle">
              Upload a PDF, DOCX, or TXT resume, add the target role description, and review the weighted skill, semantic, keyword, and structure breakdown.
            </p>
          </div>

          {errorMsg && (
            <div className="alert-banner" role="alert">
              <span>{errorMsg}</span>
              <button
                type="button"
                className="alert-close"
                aria-label="Dismiss error"
                onClick={() => setErrorMsg("")}
              >
                x
              </button>
            </div>
          )}

          <div className="workbench-grid">
            <section className="panel" aria-labelledby="resume-heading">
              <div className="panel-header">
                <h3 id="resume-heading" className="panel-title">Candidate resume</h3>
                <div className="segmented" role="tablist" aria-label="Resume input method">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={resumeInputMode === "upload"}
                    className={`seg-btn ${resumeInputMode === "upload" ? "active" : ""}`}
                    onClick={() => setResumeInputMode("upload")}
                  >
                    Upload file
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={resumeInputMode === "paste"}
                    className={`seg-btn ${resumeInputMode === "paste" ? "active" : ""}`}
                    onClick={() => setResumeInputMode("paste")}
                  >
                    Paste text
                  </button>
                </div>
              </div>

              {resumeInputMode === "upload" ? (
                <>
                  <div
                    className={`dropzone ${isDragging ? "dragging" : ""}`}
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragging(true);
                    }}
                    onDragLeave={() => setIsDragging(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragging(false);
                      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                        handleFileUpload(e.dataTransfer.files[0]);
                      }
                    }}
                  >
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx,.txt"
                      style={{ display: "none" }}
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          handleFileUpload(e.target.files[0]);
                        }
                      }}
                    />
                    <p className="dropzone-title">
                      {isParsing ? "Extracting document text..." : "Drop a PDF, DOCX, or TXT resume here"}
                    </p>
                    <p className="dropzone-sub">Maximum file size 10 MB. Multi-page PDFs and DOCX tables are supported.</p>
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={(e) => {
                        e.stopPropagation();
                        fileInputRef.current && fileInputRef.current.click();
                      }}
                    >
                      Choose file
                    </button>
                  </div>

                  {uploadedMeta && (
                    <div className="file-meta-bar">
                      <span>
                        <strong>{uploadedMeta.filename}</strong> ({uploadedMeta.file_type.toUpperCase()})
                      </span>
                      <span>
                        {uploadedMeta.word_count} words, {uploadedMeta.estimated_pages} page(s)
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <textarea
                  aria-label="Resume text"
                  className="textarea-input"
                  placeholder="Paste plain resume text here..."
                  value={resumeText}
                  onChange={(e) => setResumeText(e.target.value)}
                />
              )}

              {candidateInfo && (
                <div className="candidate-strip">
                  <span><strong>Name:</strong> {candidateInfo.candidate_name || "Candidate"}</span>
                  <span><strong>Email:</strong> {candidateInfo.email || "Not detected"}</span>
                  <span><strong>Phone:</strong> {candidateInfo.phone || "Not detected"}</span>
                </div>
              )}

              <div className="panel-footer">
                <span>{countWords(resumeText)} words loaded</span>
                {resumeText && resumeInputMode === "upload" && (
                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => setResumeInputMode("paste")}
                  >
                    Inspect or edit text
                  </button>
                )}
              </div>
            </section>

            <section className="panel" aria-labelledby="jd-heading">
              <div className="panel-header">
                <h3 id="jd-heading" className="panel-title">Target job description</h3>
              </div>

              <div>
                <label className="field-label" htmlFor="sample-jd-select">
                  Sample role preset
                </label>
                <select
                  id="sample-jd-select"
                  className="select-input"
                  value={selectedSampleJD}
                  onChange={handleSampleChange}
                >
                  <option value="custom">Custom job description</option>
                  {Object.keys(sampleJDs).map((roleName) => (
                    <option key={roleName} value={roleName}>
                      {roleName}
                    </option>
                  ))}
                </select>
              </div>

              <textarea
                aria-label="Job description text"
                className="textarea-input"
                placeholder="Paste the job responsibilities, required skills, and qualifications..."
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value);
                  setSelectedSampleJD("custom");
                }}
              />

              <div className="panel-footer">
                <span>{countWords(jdText)} words</span>
                <span>40% skills + 35% semantic + 15% keywords + 10% structure</span>
              </div>
            </section>
          </div>

          <div className="action-bar">
            <div className="weight-summary">
              <span>Active weights:</span>
              <span className="weight-chip">Skills {Math.round(normalizedWeights.skill_match * 100)}%</span>
              <span className="weight-chip">Semantic {Math.round(normalizedWeights.semantic_relevance * 100)}%</span>
              <span className="weight-chip">Keywords {Math.round(normalizedWeights.keyword_density * 100)}%</span>
              <span className="weight-chip">Structure {Math.round(normalizedWeights.structural_health * 100)}%</span>
            </div>

            <div className="btn-group">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSettingsOpen((prev) => !prev)}
              >
                Adjust weights
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleAnalyze}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? "Analyzing..." : "Analyze resume"}
              </button>
            </div>
          </div>

          {results && (
            <section className="results-section" ref={resultsRef} aria-label="ATS screening results">
              <div className="score-band">
                <div className="gauge-box">
                  <ScoreRing score={results.ats_score} />
                  <span className={`verdict-pill ${verdictTone}`}>{results.verdict}</span>
                </div>

                <div className="score-details">
                  <div>
                    <h2 className="score-headline">
                      {results.candidate_info?.candidate_name || "Candidate"} evaluation
                    </h2>
                    <p className="score-summary">{results.verdict_message}</p>
                  </div>

                  <div className="subscores-grid">
                    <div className="subscore-tile">
                      <div className="subscore-label">Skills match</div>
                      <div className="subscore-num">{results.skill_match_score}%</div>
                      <div className="meter-track">
                        <div className="meter-fill" style={{ width: `${results.skill_match_score}%` }}></div>
                      </div>
                    </div>

                    <div className="subscore-tile">
                      <div className="subscore-label">Semantic relevance</div>
                      <div className="subscore-num">{results.semantic_score}%</div>
                      <div className="meter-track">
                        <div className="meter-fill" style={{ width: `${results.semantic_score}%` }}></div>
                      </div>
                    </div>

                    <div className="subscore-tile">
                      <div className="subscore-label">Keyword context</div>
                      <div className="subscore-num">{results.keyword_density_score}%</div>
                      <div className="meter-track">
                        <div className="meter-fill" style={{ width: `${results.keyword_density_score}%` }}></div>
                      </div>
                    </div>

                    <div className="subscore-tile">
                      <div className="subscore-label">Structure health</div>
                      <div className="subscore-num">{results.structure_score}%</div>
                      <div className="meter-track">
                        <div className="meter-fill" style={{ width: `${results.structure_score}%` }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="tabs-bar" role="tablist" aria-label="Detailed evaluation views">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={activeTab === tab.id}
                    className={`tab-btn ${activeTab === tab.id ? "active" : ""}`}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="tab-panel">
                {activeTab === "skills" && (
                  <div>
                    <h3 className="section-heading">Skill gap analysis</h3>
                    <p className="section-desc">
                      Compares technical and soft competencies extracted from the job description against the candidate resume.
                    </p>

                    <div className="two-col-cards">
                      <div className="card">
                        <h4 className="card-title">
                          Matched skills ({results.matched_skills.length})
                        </h4>
                        <p className="card-sub">Present in both the resume and job description.</p>
                        {results.matched_skills.length ? (
                          <div className="pill-list">
                            {results.matched_skills.map((skill) => (
                              <span key={skill} className="skill-pill matched">
                                {titleCaseSkill(skill)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="helper-text">No direct ontology skill matches were found.</p>
                        )}
                      </div>

                      <div className="card">
                        <h4 className="card-title">
                          Missing required skills ({results.missing_skills.length})
                        </h4>
                        <p className="card-sub">Requested in the job description but absent from the resume.</p>
                        {results.missing_skills.length ? (
                          <div className="pill-list">
                            {results.missing_skills.map((skill) => (
                              <span key={skill} className="skill-pill missing">
                                {titleCaseSkill(skill)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="helper-text">All extracted job requirements are covered in the resume.</p>
                        )}
                      </div>
                    </div>

                    {Object.keys(results.skills_breakdown || {}).length > 0 && (
                      <div className="table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Domain</th>
                              <th>Required</th>
                              <th>Matched</th>
                              <th>Missing</th>
                              <th>Coverage</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.entries(results.skills_breakdown).map(([domain, info]) => {
                              const pct = Math.round((info.match_rate || 0) * 100);
                              return (
                                <tr key={domain}>
                                  <td><strong>{domain}</strong></td>
                                  <td>{info.jd_skills.length}</td>
                                  <td>
                                    {info.matched.length
                                      ? info.matched.map(titleCaseSkill).join(", ")
                                      : "None"}
                                  </td>
                                  <td>
                                    {info.missing.length
                                      ? info.missing.map(titleCaseSkill).join(", ")
                                      : "None"}
                                  </td>
                                  <td>
                                    <div className="rate-cell">
                                      <div className="rate-track">
                                        <div className="rate-fill" style={{ width: `${pct}%` }}></div>
                                      </div>
                                      <span className="mono-val">{pct}%</span>
                                    </div>
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "charts" && (
                  <div>
                    <h3 className="section-heading">Visual relevance and competency charts</h3>
                    <p className="section-desc">
                      Domain coverage radar paired with top TF-IDF n-gram phrases extracted from the job description.
                    </p>

                    <div className="two-col-cards">
                      <div className="card">
                        <h4 className="card-title">Competency radar</h4>
                        <p className="card-sub">Candidate matched skill counts compared with job requirements.</p>
                        <CompetencyRadar breakdown={results.skills_breakdown} />
                      </div>

                      <div className="card">
                        <h4 className="card-title">Top job description phrases</h4>
                        <p className="card-sub">Highest-weighted TF-IDF terms from the target role.</p>
                        <div className="kw-bar-list">
                          {(results.jd_keywords || []).slice(0, 12).map((kw) => {
                            const isMatched = (results.matched_keywords || []).includes(kw);
                            return (
                              <div key={kw} className="kw-row">
                                <span className="kw-name" title={kw}>{titleCaseSkill(kw)}</span>
                                <div className="kw-track">
                                  <div className={`kw-fill ${isMatched ? "matched" : "missing"}`}></div>
                                </div>
                                <span className={`kw-status ${isMatched ? "matched" : "missing"}`}>
                                  {isMatched ? "Matched" : "Missing"}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "audit" && (
                  <div>
                    <h3 className="section-heading">ATS readability audit</h3>
                    <p className="section-desc">
                      Checks section headings, resume length, action verbs, and quantifiable impact metrics.
                    </p>

                    <div className="two-col-cards">
                      <div className="card">
                        <h4 className="card-title">
                          Standard sections ({results.structure_audit.sections_detected} of {results.structure_audit.total_sections})
                        </h4>
                        <p className="card-sub">Explicit headings help automated parsers categorize candidate history.</p>
                        <ul className="audit-list">
                          {Object.entries(results.structure_audit.sections || {}).map(([sec, present]) => (
                            <li key={sec} className="audit-row">
                              <span>{sec}</span>
                              <span className={`audit-badge ${present ? "found" : "missing"}`}>
                                {present ? "Detected" : "Missing"}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="card">
                        <h4 className="card-title">Content and impact signals</h4>
                        <div className="metric-block">
                          <div className="metric-block-title">
                            Word count: {results.structure_audit.word_count} words
                          </div>
                          <p className="helper-text">{results.structure_audit.length_feedback}</p>
                        </div>

                        <div className="metric-block">
                          <div className="metric-block-title">
                            Action verbs detected ({results.structure_audit.action_verbs_found.length})
                          </div>
                          {results.structure_audit.action_verbs_found.length ? (
                            <div className="pill-list" style={{ marginTop: "8px" }}>
                              {results.structure_audit.action_verbs_found.map((verb) => (
                                <span key={verb} className="skill-pill neutral">{verb}</span>
                              ))}
                            </div>
                          ) : (
                            <p className="helper-text">No standard action verbs detected.</p>
                          )}
                        </div>

                        <div className="metric-block">
                          <div className="metric-block-title">
                            Quantifiable metrics ({results.structure_audit.metrics_found.length})
                          </div>
                          {results.structure_audit.metrics_found.length ? (
                            <div className="pill-list" style={{ marginTop: "8px" }}>
                              {results.structure_audit.metrics_found.map((m, i) => (
                                <span key={`${m}-${i}`} className="skill-pill matched">{m}</span>
                              ))}
                            </div>
                          ) : (
                            <p className="helper-text">No percentages, counts, or scale metrics found.</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "advice" && (
                  <div>
                    <h3 className="section-heading">Prioritized recommendations</h3>
                    <p className="section-desc">
                      Specific edits ranked by impact on ATS parsing and skill alignment.
                    </p>

                    <div className="recom-list">
                      {(results.suggestions || []).map((item, idx) => {
                        const priorityClass = (item.priority || "info").toLowerCase();
                        return (
                          <article key={idx} className={`recom-card ${priorityClass}`}>
                            <div className="recom-header">
                              <h4 className="recom-title">{item.title}</h4>
                              <span className={`priority-tag ${priorityClass}`}>
                                {item.priority} priority
                              </span>
                            </div>
                            <p className="helper-text" style={{ marginTop: 0 }}>{item.advice}</p>
                          </article>
                        );
                      })}
                    </div>

                    <div className="xyz-guide">
                      <h4 className="card-title">Bullet rewriting formula (X-Y-Z)</h4>
                      <p className="card-sub">
                        Frame each bullet around what you accomplished [X], measured by [Y], by doing [Z].
                      </p>
                      <div className="xyz-examples">
                        <div className="xyz-row">
                          <div className="xyz-weak">Weak: Responsible for writing backend APIs.</div>
                          <div className="xyz-strong">
                            Strong: Engineered 14 REST microservices in FastAPI with PostgreSQL, cutting p95 latency by 42% across 500k daily requests.
                          </div>
                        </div>
                        <div className="xyz-row">
                          <div className="xyz-weak">Weak: Worked on Machine Learning models.</div>
                          <div className="xyz-strong">
                            Strong: Fine-tuned BERT classifiers with PyTorch and Hugging Face, raising document tagging accuracy from 78% to 94%.
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {activeTab === "gemini" && (
                  <div>
                    <h3 className="section-heading">Gemini AI recruiter critique</h3>
                    <p className="section-desc">
                      Generate executive assessment, bullet rewrites, and likely interview questions using Google Gemini 2.5 Flash.
                    </p>

                    <div className="ai-controls">
                      <div className="ai-key-field">
                        <label className="field-label" htmlFor="tab-gemini-key">
                          Gemini API key {effectiveGeminiAvailable ? "(ready)" : "(required if GEMINI_API_KEY is unset)"}
                        </label>
                        <input
                          id="tab-gemini-key"
                          type="password"
                          className="text-input"
                          placeholder="Paste your Google AI Studio API key"
                          value={apiKey}
                          onChange={(e) => setApiKey(e.target.value)}
                        />
                      </div>
                      <button
                        type="button"
                        className="btn-primary"
                        onClick={handleGenerateGemini}
                        disabled={isGeneratingAI}
                      >
                        {isGeneratingAI ? "Generating critique..." : "Generate critique"}
                      </button>
                    </div>

                    {geminiCritique ? (
                      <div>
                        <div className="ai-verdict-box">
                          <div style={{ fontSize: "13px", color: "#93c5fd", marginBottom: "6px" }}>
                            Hiring recommendation: {geminiCritique.hiring_verdict || "Under Review"}
                          </div>
                          <p style={{ margin: 0, lineHeight: 1.6 }}>
                            {geminiCritique.executive_summary}
                          </p>
                        </div>

                        {Array.isArray(geminiCritique.tailored_bullet_rewrites) && (
                          <div className="card" style={{ marginBottom: "18px" }}>
                            <h4 className="card-title">Tailored bullet rewrites</h4>
                            <div className="xyz-examples">
                              {geminiCritique.tailored_bullet_rewrites.map((rw, idx) => (
                                <div key={idx} className="xyz-row">
                                  <div className="xyz-weak">Original: {rw.original_weak_phrase}</div>
                                  <div className="xyz-strong">Improved: {rw.improved_powerful_bullet}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {Array.isArray(geminiCritique.top_interview_questions) && (
                          <div className="card">
                            <h4 className="card-title">Predicted interview questions</h4>
                            <ol className="question-list">
                              {geminiCritique.top_interview_questions.map((q, idx) => (
                                <li key={idx}>{q}</li>
                              ))}
                            </ol>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="card">
                        <p className="helper-text" style={{ marginTop: 0 }}>
                          Provide an API key above and select Generate critique to inspect AI-tailored rewrites and interview prompts.
                        </p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === "export" && (
                  <div>
                    <h3 className="section-heading">Export ATS audit report</h3>
                    <p className="section-desc">
                      Download the structured evaluation as a plain-text report or copy it to the clipboard.
                    </p>

                    <div className="btn-group" style={{ marginBottom: "16px" }}>
                      <button type="button" className="btn-primary" onClick={handleDownloadReport}>
                        Download report (.txt)
                      </button>
                      <button type="button" className="btn-secondary" onClick={handleCopyReport}>
                        {copiedReport ? "Copied" : "Copy report"}
                      </button>
                    </div>

                    <pre className="report-preview">{reportText}</pre>
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          Hire-archy ATS Screening Suite. Python Django backend with React, HTML, and CSS frontend.
        </div>
      </footer>
    </div>
  );
}

const rootElement = document.getElementById("root");
ReactDOM.createRoot(rootElement).render(<App />);
