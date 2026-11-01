import React from 'react';
import Editor from '@monaco-editor/react';

export default function XsltEditor({ value, onChange, readOnly = false }) {
  return (
    <div className="editor">
      <Editor
        height="480px"
        language="xml"
        theme="vs-dark"
        value={value || '<!-- Generated XSLT will appear here -->'}
        onChange={v => onChange?.(v || '')}
        options={{
          readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          fontFamily: "'JetBrains Mono', Consolas, monospace",
          wordWrap: 'on',
          automaticLayout: true,
          scrollBeyondLastLine: false,
          padding: { top: 12, bottom: 12 },
          lineNumbersMinChars: 3,
          glyphMargin: false,
          folding: true,
          renderLineHighlight: 'gutter',
          smoothScrolling: true,
          cursorBlinking: 'smooth',
        }}
      />
    </div>
  );
}
