import React from 'react';
import { Upload, FileCheck } from 'lucide-react';

export default function FileUploader({ label, accept, onChange, file, help }) {
  return (
    <label className="upload">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Upload size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
        <span>{label}</span>
      </div>
      <input
        type="file"
        accept={accept}
        onChange={e => onChange(e.target.files?.[0] || null)}
      />
      {file && (
        <div className="file-info">
          <FileCheck size={14} />
          <span>{file.name} · {(file.size / 1024).toFixed(1)} KB</span>
        </div>
      )}
      {help && <small>{help}</small>}
    </label>
  );
}
