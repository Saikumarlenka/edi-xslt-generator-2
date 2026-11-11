import React, { useEffect, useState, useCallback } from 'react';
import {
  FileCode2, Files, Upload, Eye, Activity, Download,
  AlertTriangle, CheckCircle2, RefreshCw, Zap, Sparkles, Copy, Check,
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
import XsltEditor from './components/XsltEditor';
import DiffViewer from './components/DiffViewer';
import ValidationReport from './components/ValidationReport';
import JobProgress from './components/JobProgress';

export default function App() {
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
  const [useGemini, setUseGemini] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('upload'); // 'upload' | 'mapping' | 'xslt' | 'references'
  const [copied, setCopied] = useState(false);
  const [showDiff, setShowDiff] = useState(false);

  const hasChanges = editableMappings !== null && originalMappings !== null
    && JSON.stringify(editableMappings) !== JSON.stringify(originalMappings);

  const refreshRefs = useCallback(async (t = tx) => {
    try {
      setRefs(await getReferences(t));
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  }, [tx]);

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

  // Job Polling
  useEffect(() => {
    if (!job?.job_id) return;
    const terminal = ['completed', 'completed_with_warnings', 'failed', 'extracted'];
    if (terminal.includes(job.status)) return;

    const timer = setInterval(async () => {
      try {
        const j = await getJob(job.job_id);
        setJob(j);

        if (j.status === 'extracted') {
          clearInterval(timer);
          try {
            const m = await getMapping(j.job_id);
            setEditableMappings(m.mappings);
            setOriginalMappings(JSON.parse(JSON.stringify(m.mappings)));
            setTab('mapping');
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
              setTab('xslt');
            } catch (e) {
              setError(e.response?.data?.detail || e.message);
            }
          }
        }
      } catch (e) {
        setError(e.response?.data?.detail || e.message);
      }
    }, 2000);

    return () => clearInterval(timer);
  }, [job?.job_id, job?.status]);

  const upload = async (kind, file) => {
    setError('');
    try {
      await uploadReference(tx, kind, file);
      await refreshRefs();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const handleExtract = async () => {
    if (!matrix) {
      setError('Please upload a mapping matrix (.docx) file first.');
      return;
    }
    setError('');
    setBusy(true);
    setEditableMappings(null);
    setOriginalMappings(null);
    setSpec(null);
    setJob(null);
    setXslt('');
    setReport(null);
    try {
      const method = useGemini ? 'gemini' : 'python';
      const j = await extractMatrix(tx, matrix, method);
      setJob(j);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

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

  const handleGenerate = async () => {
    if (!job?.job_id) return;
    setError('');
    setBusy(true);
    try {
      const j = await generateXslt(job.job_id);
      setJob(j);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setBusy(false);
    }
  };

  const handleCopyXslt = () => {
    if (!xslt) return;
    navigator.clipboard.writeText(xslt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="app-shell">
      {/* ── Sidebar ──────────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <FileCode2 size={20} />
          </div>
          <div>
            <strong>EDI Studio</strong>
            <small>Mapping Generator</small>
          </div>
        </div>

        <nav>
          <button
            className={tab === 'upload' ? 'selected' : ''}
            onClick={() => setTab('upload')}
          >
            <Upload size={16} /> 1. Upload & Extract
          </button>
          <button
            className={tab === 'mapping' ? 'selected' : ''}
            onClick={() => setTab('mapping')}
            disabled={!editableMappings}
          >
            <Eye size={16} /> 2. Mapping Table
            {editableMappings && (
              <span className="clean-badge segment" style={{ marginLeft: 'auto', fontSize: '10px' }}>
                {editableMappings.length}
              </span>
            )}
          </button>
          <button
            className={tab === 'xslt' ? 'selected' : ''}
            onClick={() => setTab('xslt')}
            disabled={!xslt}
          >
            <Activity size={16} /> 3. Generated XSLT
            {xslt && (
              <span className="clean-badge" style={{ marginLeft: 'auto', color: 'var(--green)', fontSize: '10px' }}>
                Ready
              </span>
            )}
          </button>
          <button
            className={tab === 'references' ? 'selected' : ''}
            onClick={() => setTab('references')}
          >
            <Files size={16} /> Reference Files
          </button>
        </nav>

        <div className="sidebar-bottom">
          <span className={`dot ${health?.status === 'ok' ? 'passed' : 'failed'}`} />
          <span>Backend {health?.status === 'ok' ? 'Connected' : 'Offline'}</span>
        </div>
      </aside>

      {/* ── Main Area ────────────────────────────────────────────────────── */}
      <main className="main">
        {/* Top bar with inline transaction switcher */}
        <header className="topbar">
          <div>
            <h1>EDI XSLT Generator</h1>
            <p>Schema-validated, deterministic EDI mapping & XSLT synthesis</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <TransactionSelector value={tx} onChange={setTx} />
          </div>
        </header>

        {/* Error notification */}
        {error && (
          <div className="alert" style={{ marginBottom: '16px' }}>
            <AlertTriangle size={16} />
            <span>{error}</span>
            <button onClick={() => setError('')}>Dismiss</button>
          </div>
        )}

        {/* ═══ TAB 1: Upload & Extract ═════════════════════════════════════ */}
        {tab === 'upload' && (
          <section className="panel">
            <div className="section-title">
              <div>
                <h2>Upload Mapping Matrix</h2>
                <p>
                  Upload your client mapping document (.docx). The parser will automatically extract segments,
                  detect conditions, resolve canonical schema paths, and flag any typos or loop context requirements.
                </p>
              </div>
            </div>

            <FileUploader
              label={`EDI ${tx} Mapping Matrix (.docx)`}
              accept=".docx"
              file={matrix}
              onChange={setMatrix}
              help="Select or drop your client matrix DOCX here."
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={useGemini}
                  onChange={e => setUseGemini(e.target.checked)}
                />
                Use Gemini AI model instead of deterministic Python parser
              </label>

              <button
                className="button primary"
                onClick={handleExtract}
                disabled={busy || !matrix}
              >
                <Zap size={15} />
                {busy ? 'Extracting Mappings…' : 'Extract Mappings'}
              </button>
            </div>

            {/* Active Extraction Progress */}
            {job && (
              <div style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border)' }}>
                <JobProgress job={job} />
                {job.status === 'extracted' && (
                  <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="button primary" onClick={() => setTab('mapping')}>
                      View Mapping Table ({job.mapping_count} elements) →
                    </button>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {/* ═══ TAB 2: Mapping Table & Preview ══════════════════════════════ */}
        {tab === 'mapping' && (
          <section className="panel" style={{ padding: '20px' }}>
            <div className="section-title" style={{ marginBottom: '14px' }}>
              <div>
                <h2>Mapping Table & Schema Diagnostics</h2>
                <p>
                  Review extracted mappings. Edit values or paths directly. Enclosing loop contexts and canonical suggestions are verified against the schema.
                </p>
              </div>
            </div>

            <MappingPreview
              mappings={editableMappings}
              onUpdate={setEditableMappings}
              onSave={handleSaveMappings}
              onGenerate={handleGenerate}
              hasChanges={hasChanges}
              saving={saving}
              extractionMethod={job?.extraction_method || (useGemini ? 'gemini' : 'python')}
            />
          </section>
        )}

        {/* ═══ TAB 3: Generated XSLT ═══════════════════════════════════════ */}
        {tab === 'xslt' && (
          <>
            <section className="panel">
              <div className="section-title">
                <div>
                  <h2>Generated XSLT Output</h2>
                  <p>
                    Clean XSLT 1.0 stylesheet generated strictly according to your mapping matrix.
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="button secondary sm" onClick={() => setShowDiff(!showDiff)}>
                    {showDiff ? 'Hide Diff' : 'Compare Baseline'}
                  </button>
                  <button className="button secondary sm" onClick={handleCopyXslt}>
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                  {job?.job_id && (
                    <a className="button primary sm" href={getDownloadUrl(job.job_id)}>
                      <Download size={14} /> Download ZIP
                    </a>
                  )}
                </div>
              </div>

              {showDiff ? (
                <DiffViewer original={baseline} modified={xslt} />
              ) : (
                <XsltEditor value={xslt} onChange={setXslt} />
              )}
            </section>

            {report && (
              <section className="panel">
                <div className="section-title">
                  <div>
                    <h2>Validation & Transformation Results</h2>
                    <p>Automated compilation and test XML execution status.</p>
                  </div>
                </div>
                <ValidationReport report={report} />
              </section>
            )}
          </>
        )}

        {/* ═══ TAB 4: Reference Library ════════════════════════════════════ */}
        {tab === 'references' && (
          <section className="panel">
            <div className="section-title">
              <div>
                <h2>Reference Library · EDI {tx}</h2>
                <p>Manage authoritative baseline schemas and canonical test files.</p>
              </div>
              <button className="button secondary sm" onClick={() => refreshRefs()}>
                <RefreshCw size={13} /> Refresh
              </button>
            </div>
            <ReferenceFileStatus data={refs} onUpload={upload} />
          </section>
        )}
      </main>
    </div>
  );
}
