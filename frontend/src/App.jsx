import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  Activity, FileCode2, Files, Play, RefreshCw, Download,
  AlertTriangle, CheckCircle2, Upload, Eye, Zap, Sparkles,
} from 'lucide-react';
import {
  getHealth, getReferences, uploadReference,
  extractMatrix, generateXslt,
  getJob, getMapping, updateMapping, getXslt, getReport, getDownloadUrl,
} from './services/api';

import TransactionSelector from './components/TransactionSelector';
import FileUploader from './components/FileUploader';
import ReferenceFileStatus from './components/ReferenceFileStatus';
import MappingPreview from './components/MappingPreview';
import MappingTable from './components/MappingTable';
import XsltEditor from './components/XsltEditor';
import DiffViewer from './components/DiffViewer';
import ValidationReport from './components/ValidationReport';
import JobProgress from './components/JobProgress';

export default function App() {
  // ── State ───────────────────────────────────────────────────────────────
  const [tx, setTx] = useState('210');
  const [health, setHealth] = useState(null);
  const [refs, setRefs] = useState(null);
  const [matrix, setMatrix] = useState(null);
  const [job, setJob] = useState(null);
  const [editableMappings, setEditableMappings] = useState(null);
  const [originalMappings, setOriginalMappings] = useState(null);
  const [spec, setSpec] = useState(null);
  const [xslt, setXslt] = useState('');
  const [baseline, setBaseline] = useState('');
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);
  const [activeMethod, setActiveMethod] = useState('python');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('generate');

  const hasChanges = editableMappings !== null && originalMappings !== null
    && JSON.stringify(editableMappings) !== JSON.stringify(originalMappings);

  // ── Workflow step computation ───────────────────────────────────────────
  const getStep = () => {
    if (!job) return 1;
    if (job.status === 'extracted' || (job.status === 'running' && job.stage === 'matrix_interpretation')) return 2;
    if (['completed', 'completed_with_warnings'].includes(job.status)) return 4;
    if (job.status === 'running') return 3;
    if (job.status === 'failed') return job.stage === 'failed' && !spec ? 1 : 3;
    return 1;
  };
  const currentStep = getStep();

  // ── Reference refresh ───────────────────────────────────────────────────
  const refreshRefs = useCallback(async (t = tx) => {
    try {
      setRefs(await getReferences(t));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, [tx]);

  // ── Init ────────────────────────────────────────────────────────────────
  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: 'offline' }));
    refreshRefs('210');
  }, []);

  useEffect(() => {
    refreshRefs(tx);
    setMatrix(null);
    setJob(null);
    setEditableMappings(null);
    setOriginalMappings(null);
    setSpec(null);
    setXslt('');
    setBaseline('');
    setReport(null);
  }, [tx]);

  // ── Job polling ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!job?.job_id) return;
    const terminal = ['completed', 'completed_with_warnings', 'failed', 'extracted'];
    if (terminal.includes(job.status)) return;

    const timer = setInterval(async () => {
      try {
        const j = await getJob(job.job_id);
        setJob(j);

        if (j.status === 'extracted') {
          // Matrix extracted — load mapping for preview
          clearInterval(timer);
          try {
            const m = await getMapping(j.job_id);
            setEditableMappings(m.mappings);
            setOriginalMappings(JSON.parse(JSON.stringify(m.mappings)));
            setTab('preview');
          } catch (e) {
            setError(e.response?.data?.detail || e.message);
          }
        } else if (['completed', 'completed_with_warnings', 'failed'].includes(j.status)) {
          clearInterval(timer);
          if (j.status !== 'failed') {
            try {
              const [m, x, r] = await Promise.all([
                getMapping(j.job_id),
                getXslt(j.job_id),
                getReport(j.job_id),
              ]);
              setSpec(m);
              setXslt(x.content);
              setBaseline(x.content);
              setReport(r);
              setTab('review');
            } catch (e) {
              setError(e.response?.data?.detail || e.message);
            }
          }
        }
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      }
    }, 2500);

    return () => clearInterval(timer);
  }, [job?.job_id, job?.status]);

  // ── Actions ─────────────────────────────────────────────────────────────

  const upload = async (kind, file) => {
    setError('');
    try {
      await uploadReference(tx, kind, file);
      await refreshRefs();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  /** Step 1: Extract matrix from DOCX (Python or Gemini) */
  const handleExtract = async (method = 'python') => {
    if (!matrix) {
      setError('Upload the mapping matrix DOCX first.');
      return;
    }
    setError('');
    setActiveMethod(method);
    setBusy(true);
    setEditableMappings(null);
    setOriginalMappings(null);
    setSpec(null);
    setJob(null);
    setXslt('');
    setReport(null);
    try {
      const j = await extractMatrix(tx, matrix, method);
      setJob(j);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  /** Save edited mappings to backend */
  const handleSaveMappings = async () => {
    if (!job?.job_id || !editableMappings) return;
    setSaving(true);
    setError('');
    try {
      await updateMapping(job.job_id, editableMappings);
      setOriginalMappings(JSON.parse(JSON.stringify(editableMappings)));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setSaving(false);
    }
  };

  /** Step 2: Generate XSLT from the (edited) mapping */
  const handleGenerate = async () => {
    if (!job?.job_id) return;
    setError('');
    setBusy(true);
    try {
      const j = await generateXslt(job.job_id);
      setJob(j);
      setTab('generate'); // Switch back to see progress
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  /** Reload existing results */
  const loadExisting = async () => {
    if (!job?.job_id) return;
    setBusy(true);
    try {
      const [m, x, r] = await Promise.all([
        getMapping(job.job_id),
        getXslt(job.job_id),
        getReport(job.job_id),
      ]);
      setSpec(m);
      setXslt(x.content);
      setBaseline(x.content);
      setReport(r);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="app-shell">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <FileCode2 size={22} />
          </div>
          <div>
            <strong>EDI Studio</strong>
            <small>Mapping Workbench</small>
          </div>
        </div>

        <nav>
          <button
            className={tab === 'generate' ? 'selected' : ''}
            onClick={() => setTab('generate')}
          >
            <Upload size={17} /> Upload & Extract
          </button>
          <button
            className={tab === 'preview' ? 'selected' : ''}
            onClick={() => setTab('preview')}
            disabled={!editableMappings}
          >
            <Eye size={17} /> Preview & Edit
          </button>
          <button
            className={tab === 'references' ? 'selected' : ''}
            onClick={() => setTab('references')}
          >
            <Files size={17} /> Reference Library
          </button>
          <button
            className={tab === 'review' ? 'selected' : ''}
            onClick={() => setTab('review')}
          >
            <Activity size={17} /> Results & Review
          </button>
        </nav>

        <div className="sidebar-bottom">
          <span className={`dot ${health?.status === 'ok' ? 'passed' : 'failed'}`} />
          <span>Backend {health?.status === 'ok' ? 'connected' : 'unavailable'}</span>
          <small>{health?.model || 'Gemini status unknown'}</small>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────────────────────────────── */}
      <main className="main">
        <header className="topbar">
          <div>
            <div className="eyebrow">Integration Engineering / Workspace</div>
            <h1>EDI XSLT Generator</h1>
            <p>Schema-aware mapping analysis for EDI 210 and 214</p>
          </div>
          <div className="top-chip">
            <span className={`dot ${health?.gemini_configured ? 'passed' : 'warning'}`} />
            {health?.gemini_configured ? 'Gemini configured' : 'Gemini key missing'}
          </div>
        </header>

        {/* ── Error alert ──────────────────────────────────────────────── */}
        {error && (
          <div className="alert">
            <AlertTriangle size={18} />
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        {/* ── Workflow steps indicator ─────────────────────────────────── */}
        <div className="workflow-steps">
          <div className={`workflow-step ${currentStep === 1 ? 'active' : currentStep > 1 ? 'completed' : ''}`}>
            <span className="step-num">{currentStep > 1 ? '✓' : '1'}</span>
            <div className="step-info">
              <h4>Upload Matrix</h4>
              <small>Upload DOCX document</small>
            </div>
          </div>
          <div className={`step-connector ${currentStep > 1 ? 'done' : ''}`} />
          <div className={`workflow-step ${currentStep === 2 ? 'active' : currentStep > 2 ? 'completed' : ''}`}>
            <span className="step-num">{currentStep > 2 ? '✓' : '2'}</span>
            <div className="step-info">
              <h4>Preview & Edit</h4>
              <small>Review extracted mappings</small>
            </div>
          </div>
          <div className={`step-connector ${currentStep > 2 ? 'done' : ''}`} />
          <div className={`workflow-step ${currentStep === 3 ? 'active' : currentStep > 3 ? 'completed' : ''}`}>
            <span className="step-num">{currentStep > 3 ? '✓' : '3'}</span>
            <div className="step-info">
              <h4>Generate XSLT</h4>
              <small>AI-assisted generation</small>
            </div>
          </div>
          <div className={`step-connector ${currentStep > 3 ? 'done' : ''}`} />
          <div className={`workflow-step ${currentStep === 4 ? 'active' : ''}`}>
            <span className="step-num">4</span>
            <div className="step-info">
              <h4>Review & Download</h4>
              <small>Validate and export</small>
            </div>
          </div>
        </div>

        {/* ── Transaction selector ─────────────────────────────────────── */}
        <section className="panel transaction-panel">
          <div>
            <h2>Transaction Type</h2>
            <p className="muted">
              Select the transaction whose matrix and reference assets you are working with.
            </p>
          </div>
          <TransactionSelector value={tx} onChange={setTx} />
        </section>

        {/* ═══ TAB: Upload & Extract ══════════════════════════════════════ */}
        {tab === 'generate' && (
          <>
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Upload Mapping Matrix</h2>
                  <p>
                    Choose your extraction model: use our fast, deterministic <strong>Python Matrix Parser</strong> for exact, noise-free matrix extraction (with automatic constants, condition inheritance, and crossed-out detection), or use <strong>Gemini AI</strong>.
                  </p>
                </div>
                <span className="step-number">01</span>
              </div>

              <FileUploader
                label="Mapping matrix (.docx)"
                accept=".docx"
                file={matrix}
                onChange={setMatrix}
                help="Upload your EDI mapping matrix DOCX. Select an extraction method below."
              />

              <div className="readiness">
                <strong>Reference readiness</strong>
                <span className={refs?.ready ? 'good' : 'not-ready'}>
                  {refs?.ready ? 'Required files present' : 'Missing required reference files'}
                </span>
                <button className="text-button" onClick={() => setTab('references')}>
                  Manage references →
                </button>
              </div>

              {/* Dual Extraction Actions: Python and Gemini */}
              <div className="extraction-methods-grid">
                <div className="method-box recommended">
                  <div className="method-box-header">
                    <span className="method-badge python">🐍 Python Matrix Parser</span>
                    <span className="badge-tag">Fast & Deterministic</span>
                  </div>
                  <h4>Direct Matrix Extraction</h4>
                  <p>
                    Reads exact cells from the matrix with blocking skills for unwanted noise. Automatically detects segment conditions, canonical paths, constants (when no path), and crossed-out/suppressed items.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => handleExtract('python')}
                    disabled={busy || !matrix}
                  >
                    <Zap size={16} />
                    {busy && activeMethod === 'python' ? 'Extracting via Python…' : 'Extract with Python'}
                  </button>
                </div>

                <div className="method-box">
                  <div className="method-box-header">
                    <span className="method-badge gemini">✨ Google Gemini AI</span>
                    <span className="badge-tag">LLM Interpretation</span>
                  </div>
                  <h4>Gemini Multimodal Model</h4>
                  <p>
                    Interprets document text, footnotes, and complex layout notes using Google Gemini AI.
                  </p>
                  <button
                    className="button secondary"
                    onClick={() => handleExtract('gemini')}
                    disabled={busy || !matrix}
                  >
                    <Sparkles size={16} />
                    {busy && activeMethod === 'gemini' ? 'Extracting via Gemini…' : 'Extract with Gemini'}
                  </button>
                </div>
              </div>
            </section>

            {/* Job progress (shows during extraction or generation) */}
            {job && (
              <section className="panel">
                <div className="section-title">
                  <div>
                    <h2>Job Progress</h2>
                    <p>Job ID: <code>{job.job_id}</code></p>
                  </div>
                </div>
                <JobProgress job={job} />
                {job.status === 'failed' && (
                  <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
                    <button
                      className="button primary"
                      onClick={() => handleExtract('python')}
                    >
                      <Zap size={15} /> Retry with Python
                    </button>
                    <button
                      className="button secondary"
                      onClick={() => handleExtract('gemini')}
                    >
                      <Sparkles size={15} /> Retry with Gemini
                    </button>
                  </div>
                )}
                {job.status === 'extracted' && (
                  <button
                    className="button primary"
                    onClick={() => setTab('preview')}
                    style={{ marginTop: '12px' }}
                  >
                    <Eye size={16} /> Review Extracted Mappings ({job.mapping_count} elements) →
                  </button>
                )}
              </section>
            )}
          </>
        )}

        {/* ═══ TAB: Preview & Edit ════════════════════════════════════════ */}
        {tab === 'preview' && (
          <section className="panel">
            <div className="section-title">
              <div>
                <h2>Mapping Preview & Editor</h2>
                <p>
                  Review and correct the extracted mapping data below. Click any cell
                  to edit. Save your changes, then generate XSLT.
                </p>
              </div>
              <span className="step-number">02</span>
            </div>

            <MappingPreview
              mappings={editableMappings}
              onUpdate={setEditableMappings}
              onSave={handleSaveMappings}
              onGenerate={handleGenerate}
              hasChanges={hasChanges}
              saving={saving}
              extractionMethod={job?.extraction_method || activeMethod}
            />
          </section>
        )}

        {/* ═══ TAB: Reference Library ═════════════════════════════════════ */}
        {tab === 'references' && (
          <section className="panel">
            <div className="section-title">
              <div>
                <h2>Reference Library · EDI {tx}</h2>
                <p>Upload the standard map and schemas used as the baseline.</p>
              </div>
              <button className="button secondary" onClick={() => refreshRefs()}>
                <RefreshCw size={15} /> Refresh
              </button>
            </div>
            <ReferenceFileStatus data={refs} onUpload={upload} />
            <p className="hint">
              Required for generation: standard XSLT, canonical XSD, EDI XSD, and
              canonical test XML. Upload sample maps optionally. Matrix DOCX can be
              supplied on the Upload & Extract tab.
            </p>
          </section>
        )}

        {/* ═══ TAB: Results & Review ══════════════════════════════════════ */}
        {tab === 'review' && (
          <>
            {/* Mapping specification */}
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Mapping Specification</h2>
                  <p>
                    Review extracted requirements, source paths, destination fields
                    and implementation status after XSLT generation.
                  </p>
                </div>
                <button
                  className="button secondary"
                  onClick={loadExisting}
                  disabled={busy || !job?.job_id}
                >
                  <RefreshCw size={15} /> Reload
                </button>
              </div>
              <MappingTable spec={spec} />
            </section>

            {/* Generated XSLT */}
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Generated XSLT</h2>
                  <p>
                    Monaco XML editor. The baseline is preserved when a safe,
                    map-specific patch cannot be applied.
                  </p>
                </div>
                {job?.job_id && (
                  <a className="button secondary" href={getDownloadUrl(job.job_id)}>
                    <Download size={15} /> Download ZIP
                  </a>
                )}
              </div>
              <XsltEditor value={xslt} onChange={setXslt} />
              <div className="hint">
                <AlertTriangle size={15} />
                Editing here changes the local review buffer only; it does not modify
                the backend artifact or run validation.
              </div>
            </section>

            {/* Baseline comparison */}
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Baseline Comparison</h2>
                  <p>Compare the preserved baseline against the current editor content.</p>
                </div>
              </div>
              <DiffViewer original={baseline} modified={xslt} />
            </section>

            {/* Validation */}
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Validation & Coverage</h2>
                  <p>Results reflect checks actually run by the backend, not AI claims.</p>
                </div>
              </div>
              <ValidationReport report={report} />
            </section>
          </>
        )}

        <footer>
          EDI Studio · AI-assisted analysis · Review all unresolved mappings before
          using output in production.
        </footer>
      </main>
    </div>
  );
}
