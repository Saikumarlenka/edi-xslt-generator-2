import React from 'react';
import { DiffEditor } from '@monaco-editor/react';

export default function DiffViewer({ original, modified }) {
  return (
    <div className="editor">
      <DiffEditor
        height="440px"
        language="xml"
        theme="vs-dark"
        original={original || ''}
        modified={modified || ''}
        options={{
          readOnly: true,
          minimap: { enabled: false },
          renderSideBySide: true,
          automaticLayout: true,
          fontSize: 13,
          fontFamily: "'JetBrains Mono', Consolas, monospace",
          scrollBeyondLastLine: false,
          padding: { top: 12, bottom: 12 },
          smoothScrolling: true,
        }}
      />
    </div>
  );
}
