import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, MinusCircle } from 'lucide-react';

const statusIcon = (status) => {
  switch (status) {
    case 'passed': return <CheckCircle2 size={16} style={{ color: 'var(--green)', flexShrink: 0 }} />;
    case 'failed': return <XCircle size={16} style={{ color: 'var(--red)', flexShrink: 0 }} />;
    case 'warning': return <AlertTriangle size={16} style={{ color: 'var(--amber)', flexShrink: 0 }} />;
    default: return <MinusCircle size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />;
  }
};

export default function ValidationReport({ report }) {
  if (!report) {
    return (
      <div className="empty-state">
        <div className="icon"><CheckCircle2 size={24} /></div>
        <h3>No validation results</h3>
        <p>Validation results will appear after XSLT generation completes.</p>
      </div>
    );
  }

  const items = report.validation?.items || [];

  return (
    <div className="validation-list">
      {items.map((x, i) => (
        <div className="validation-item" key={i}>
          {statusIcon(x.status)}
          <div>
            <strong>{x.name}</strong>
            <p>{x.details}</p>
          </div>
          <span className={`status-pill ${x.status === 'passed' ? 'resolved' : x.status === 'failed' ? 'failed' : 'unresolved'}`}>
            {x.status}
          </span>
        </div>
      ))}

      {report.coverage && (
        <div className="coverage">
          <strong>Mapping Coverage</strong>
          <pre>{JSON.stringify(report.coverage, null, 2)}</pre>
        </div>
      )}

      {(report.warnings || []).map((w, i) => (
        <p className="warning" key={`w-${i}`}>⚠ {w}</p>
      ))}

      {(report.errors || []).map((e, i) => (
        <p className="error" key={`e-${i}`}>{e}</p>
      ))}
    </div>
  );
}
