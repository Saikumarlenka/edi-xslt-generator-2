import React, { useState, useRef } from 'react';

/**
 * An interactive expandable box for table cells.
 * Truncates gracefully in the table layout, but on hover smoothly expands
 * into an elevated, full-visibility popover card so long paths, nested conditions,
 * and complex business rules can be read with zero clipping.
 */
export default function HoverExpandBox({
  content,
  title,
  type = 'text',
  isCrossed = false,
  isConstant = false,
  emptyLabel = '—',
  maxPreviewChars = 36,
  className = '',
  editable = false,
  onChange = null,
}) {
  const [hovered, setHovered] = useState(false);
  const [active, setActive] = useState(false);
  const timerRef = useRef(null);

  const rawText = Array.isArray(content)
    ? content.filter(Boolean).join('; ')
    : String(content || '');

  const isEmpty = !rawText.trim();

  const handleMouseEnter = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setHovered(true), 120);
  };

  const handleMouseLeave = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setHovered(false);
      setActive(false);
    }, 150);
  };

  if (editable) {
    return (
      <div
        className={`hover-expand-container ${hovered ? 'elevated' : ''} ${className}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <textarea
          className={`editable-cell ${isCrossed ? 'text-crossed' : ''}`}
          value={rawText}
          onChange={e => onChange && onChange(e.target.value)}
          rows={rawText.length > 50 ? 2 : 1}
          placeholder={emptyLabel}
        />
        {hovered && rawText.length > maxPreviewChars && (
          <div className="hover-popover-card">
            {title && (
              <div className="popover-header">
                <span className="popover-title">{title}</span>
                {isConstant && <span className="popover-badge constant">Constant</span>}
                {isCrossed && <span className="popover-badge crossed">Crossed Out</span>}
              </div>
            )}
            <div className="popover-full-text font-mono">{rawText}</div>
          </div>
        )}
      </div>
    );
  }

  if (isEmpty) {
    if (isConstant) {
      return (
        <span className="badge-constant-inline">
          <span className="dot-mini constant" /> Constant (No Path)
        </span>
      );
    }
    return <span className="text-muted-dim">{emptyLabel}</span>;
  }

  const isLong = rawText.length > maxPreviewChars;

  return (
    <div
      className={`hover-expand-container ${hovered ? 'elevated' : ''} ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={() => setActive(!active)}
    >
      <div
        className={`hover-preview-text ${isCrossed ? 'text-crossed' : ''} ${
          type === 'path' || type === 'code' ? 'font-mono' : ''
        }`}
        title={isLong ? 'Hover or click to expand' : undefined}
      >
        {isConstant && !isCrossed && (
          <span className="dot-mini constant" title="Constant / Static value" />
        )}
        {isCrossed && <span className="dot-mini crossed" title="Crossed out / Commented out" />}
        {rawText}
      </div>

      {(hovered || active) && isLong && (
        <div className="hover-popover-card" onClick={e => e.stopPropagation()}>
          <div className="popover-header">
            {title && <span className="popover-title">{title}</span>}
            <div className="popover-badges">
              {isConstant && <span className="popover-badge constant">Constant Value</span>}
              {isCrossed && <span className="popover-badge crossed">Crossed Out / Excluded</span>}
              {type === 'condition' && <span className="popover-badge condition">Conditional</span>}
            </div>
          </div>
          <div
            className={`popover-full-text ${
              type === 'path' || type === 'code' ? 'font-mono' : ''
            } ${isCrossed ? 'text-crossed' : ''}`}
          >
            {rawText}
          </div>
          {isCrossed && (
            <div className="popover-footer-note">
              Marked strikethrough in matrix. Output will be commented out or suppressed in generated XSLT.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

