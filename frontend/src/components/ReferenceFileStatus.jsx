import React from 'react';
import { CheckCircle2, AlertCircle, Upload as UploadIcon } from 'lucide-react';

const labels = {
  standard_xslt: 'Standard XSLT',
  canonical_xsd: 'Canonical XSD',
  edi_xsd: 'EDI XSD',
  canonical_xml: 'Canonical test XML',
  sample_xslt: 'Sample XSLT',
};

export default function ReferenceFileStatus({ data, onUpload }) {
  const files = data?.files || {};

  return (
    <div className="ref-grid">
      {Object.entries(labels).map(([k, label]) => {
        const hasFile = k === 'sample_xslt' ? files[k]?.length > 0 : !!files[k];
        return (
          <div className="ref-item" key={k}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              {hasFile
                ? <CheckCircle2 size={16} style={{ color: 'var(--green)', flexShrink: 0 }} />
                : <AlertCircle size={16} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
              }
              <div>
                <strong>{label}</strong>
                <p>
                  {k === 'sample_xslt'
                    ? (files[k]?.length ? `${files[k].length} sample(s) uploaded` : 'Optional')
                    : (files[k]?.name || 'Missing')
                  }
                </p>
              </div>
            </div>
            <label className="mini-upload">
              <UploadIcon size={12} style={{ marginRight: '4px' }} />
              Upload
              <input
                type="file"
                accept={
                  k.includes('xslt') ? '.xsl,.xslt'
                    : k.includes('xsd') ? '.xsd'
                    : k === 'canonical_xml' ? '.xml'
                    : '.docx'
                }
                onChange={e => e.target.files?.[0] && onUpload(k, e.target.files[0])}
              />
            </label>
          </div>
        );
      })}
    </div>
  );
}
