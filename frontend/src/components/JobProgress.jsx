import React from 'react';

const stages = [
  'queued',
  'matrix_interpretation',
  'extracted',
  'reference_analysis',
  'mapping_analysis',
  'patch_review',
  'validation',
  'completed',
];

export default function JobProgress({ job }) {
  if (!job) return null;

  const idx = stages.indexOf(job.stage);
  const pct = Math.max(4, ((idx + 1) / stages.length) * 100);

  const dotClass =
    job.status === 'failed' ? 'failed'
    : job.status === 'extracted' ? 'extracted'
    : job.status.startsWith('completed') ? 'passed'
    : 'running';

  return (
    <div className="job-box">
      <div className="job-head">
        <span className={`dot ${dotClass}`} />
        <strong>{job.status.replaceAll('_', ' ')}</strong>
        <span className="muted">{job.stage.replaceAll('_', ' ')}</span>
        {job.extraction_method && (
          <span className={`method-badge-pill ${job.extraction_method}`}>
            {job.extraction_method === 'python' ? '🐍 Python Model' : '✨ Gemini Model'}
          </span>
        )}
      </div>
      <p>{job.message}</p>
      <div className="progress">
        <div style={{ width: `${pct}%` }} />
      </div>
      {job.errors?.map((e, i) => (
        <p className="error" key={i}>{e}</p>
      ))}
    </div>
  );
}
