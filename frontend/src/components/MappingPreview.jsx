import React, { useState, useMemo, useCallback } from 'react';
import {
  Search, Save, RotateCcw, ChevronDown, ChevronUp, Pencil,
  Filter, Ban, CheckCircle2, AlertCircle, Sparkles, Layers,
} from 'lucide-react';
import HoverExpandBox from './HoverExpandBox';

/**
 * Editable mapping table for previewing and correcting extracted matrix data.
 * Displays: Segment, Element, Condition, Path, Constants/Static Values, Rule, Status.
 * Hovering on any box expands it smoothly for high visibility.
 * Clearly differentiates Constants (no path) and Crossed-Out (suppressed/commented) elements.
 */

const COLUMNS = [
  { key: 'destination_segment', label: 'Segment', width: '90px', type: 'input' },
  { key: 'destination_element', label: 'Element', width: '95px', type: 'input' },
  { key: 'conditions', label: 'Condition', width: '220px', type: 'list' },
  { key: 'source_canonical_path', label: 'Path', width: '230px', type: 'input' },
  { key: 'constants', label: 'Constant / Value', width: '130px', type: 'list' },
  { key: 'mapping_rule', label: 'Mapping Rule', width: '200px', type: 'textarea' },
];

function statusClass(status, isCrossed, isConstant) {
  if (isCrossed) return 'crossed';
  if (isConstant) return 'constant';
  if (!status) return '';
  if (status.includes('implemented')) return 'implemented';
  if (status.includes('unresolved')) return 'unresolved';
  if (status.includes('failed')) return 'failed';
  if (status.includes('resolved')) return 'resolved';
  return '';
}

export default function MappingPreview({
  mappings,
  onUpdate,
  onSave,
  onGenerate,
  hasChanges,
  saving,
  readOnly = false,
  extractionMethod = 'python',
}) {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all'); // all | active | constants | conditional | crossed
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [expandedRow, setExpandedRow] = useState(null);

  // Filter and sort mappings
  const filtered = useMemo(() => {
    if (!mappings) return [];
    let rows = [...mappings];

    // Filter by type chip
    if (filterType === 'active') {
      rows = rows.filter(m => !m.is_crossed);
    } else if (filterType === 'constants') {
      rows = rows.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed));
    } else if (filterType === 'conditional') {
      rows = rows.filter(m => m.conditions && m.conditions.length > 0);
    } else if (filterType === 'crossed') {
      rows = rows.filter(m => m.is_crossed);
    }

    // Search query
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(m =>
        Object.values(m).some(v => {
          if (Array.isArray(v)) return v.some(x => String(x).toLowerCase().includes(q));
          return String(v || '').toLowerCase().includes(q);
        })
      );
    }

    // Sort column
    if (sortCol) {
      rows.sort((a, b) => {
        let va = a[sortCol];
        let vb = b[sortCol];
        if (Array.isArray(va)) va = va.join(' ');
        if (Array.isArray(vb)) vb = vb.join(' ');
        va = String(va || '').toLowerCase();
        vb = String(vb || '').toLowerCase();
        return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      });
    }

    return rows;
  }, [mappings, filterType, search, sortCol, sortDir]);

  // Statistics
  const stats = useMemo(() => {
    if (!mappings) return { total: 0, constants: 0, crossed: 0, conditional: 0, active: 0 };
    const total = mappings.length;
    const crossed = mappings.filter(m => m.is_crossed).length;
    const constants = mappings.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed)).length;
    const conditional = mappings.filter(m => m.conditions && m.conditions.length > 0).length;
    return { total, crossed, constants, conditional, active: total - crossed };
  }, [mappings]);

  const toggleSort = useCallback((col) => {
    if (sortCol === col) {
      setSortDir(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
  }, [sortCol]);

  const handleCellChange = useCallback((mappingId, field, value) => {
    if (!onUpdate) return;
    const idx = mappings.findIndex(m => m.mapping_id === mappingId);
    if (idx === -1) return;
    const updated = [...mappings];
    const item = { ...updated[idx], [field]: value };

    // Maintain consistency: if path is emptied, mark as constant
    if (field === 'source_canonical_path') {
      if (!value.trim()) {
        item.is_constant = true;
      }
    }
    updated[idx] = item;
    onUpdate(updated);
  }, [mappings, onUpdate]);

  const handleListChange = useCallback((mappingId, field, value) => {
    const items = value.split('\n').map(s => s.trim()).filter(Boolean);
    handleCellChange(mappingId, field, items);
  }, [handleCellChange]);

  const toggleCrossed = useCallback((mappingId) => {
    if (!onUpdate) return;
    const idx = mappings.findIndex(m => m.mapping_id === mappingId);
    if (idx === -1) return;
    const updated = [...mappings];
    const prev = updated[idx].is_crossed;
    updated[idx] = {
      ...updated[idx],
      is_crossed: !prev,
      implementation_status: !prev ? 'excluded_crossed_out' : 'unresolved',
    };
    onUpdate(updated);
  }, [mappings, onUpdate]);

  if (!mappings?.length) {
    return (
      <div className="empty-state">
        <div className="icon"><Pencil size={24} /></div>
        <h3>No mapping data yet</h3>
        <p>Extract a mapping matrix using Python or Gemini to view the structured table.</p>
      </div>
    );
  }

  return (
    <div className="mapping-preview-root">
      {/* ── Toolbar & Stats ────────────────────────────────────────── */}
      <div className="mapping-toolbar">
        <div className="left">
          <div className="mapping-stats">
            <button
              className={`stat-pill-btn ${filterType === 'all' ? 'active' : ''}`}
              onClick={() => setFilterType('all')}
            >
              <span className="stat-value">{stats.total}</span>
              <span className="stat-label">Total Elements</span>
            </button>
            <button
              className={`stat-pill-btn ${filterType === 'constants' ? 'active' : ''}`}
              onClick={() => setFilterType('constants')}
            >
              <span className="stat-value" style={{ color: 'var(--blue)' }}>{stats.constants}</span>
              <span className="stat-label">Constants (No Path)</span>
            </button>
            <button
              className={`stat-pill-btn ${filterType === 'conditional' ? 'active' : ''}`}
              onClick={() => setFilterType('conditional')}
            >
              <span className="stat-value" style={{ color: '#c084fc' }}>{stats.conditional}</span>
              <span className="stat-label">Conditional</span>
            </button>
            <button
              className={`stat-pill-btn ${filterType === 'crossed' ? 'active' : ''}`}
              onClick={() => setFilterType('crossed')}
            >
              <span className="stat-value" style={{ color: 'var(--text-muted)' }}>{stats.crossed}</span>
              <span className="stat-label">Crossed Out / Excluded</span>
            </button>
          </div>
        </div>

        <div className="right">
          <div className="search-box">
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search segment, path, condition, value…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Filter Tabs Sub-bar */}
      <div className="filter-chips-bar">
        <span className="filter-label"><Filter size={13} /> View:</span>
        <button
          className={`filter-chip ${filterType === 'all' ? 'selected' : ''}`}
          onClick={() => setFilterType('all')}
        >
          All ({stats.total})
        </button>
        <button
          className={`filter-chip ${filterType === 'active' ? 'selected' : ''}`}
          onClick={() => setFilterType('active')}
        >
          Active for XSLT ({stats.active})
        </button>
        <button
          className={`filter-chip ${filterType === 'constants' ? 'selected' : ''}`}
          onClick={() => setFilterType('constants')}
        >
          Constants Only ({stats.constants})
        </button>
        <button
          className={`filter-chip ${filterType === 'conditional' ? 'selected' : ''}`}
          onClick={() => setFilterType('conditional')}
        >
          Conditional ({stats.conditional})
        </button>
        <button
          className={`filter-chip ${filterType === 'crossed' ? 'selected' : ''}`}
          onClick={() => setFilterType('crossed')}
        >
          Crossed Out / Commented ({stats.crossed})
        </button>
      </div>

      {/* ── Table Wrap with Hover-Expandable Cells ─────────────────── */}
      <div className="table-wrap" style={{ maxHeight: '620px', overflowY: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: '36px' }}>#</th>
              <th
                style={{ width: '85px', cursor: 'pointer' }}
                onClick={() => toggleSort('destination_segment')}
              >
                Segment {sortCol === 'destination_segment' && (sortDir === 'asc' ? '▲' : '▼')}
              </th>
              <th
                style={{ width: '95px', cursor: 'pointer' }}
                onClick={() => toggleSort('destination_element')}
              >
                Element {sortCol === 'destination_element' && (sortDir === 'asc' ? '▲' : '▼')}
              </th>
              <th style={{ width: '220px' }}>Condition</th>
              <th style={{ width: '230px' }}>Canonical Path</th>
              <th style={{ width: '130px' }}>Constant / Value</th>
              <th style={{ width: '180px' }}>Mapping Rule</th>
              <th style={{ width: '100px' }}>Status</th>
              {!readOnly && <th style={{ width: '70px', textAlign: 'center' }}>Omit</th>}
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => {
              const isExpanded = expandedRow === m.mapping_id;
              const hasNoPath = !m.source_canonical_path || m.source_canonical_path === 'unknown';
              const isConstantEffective = m.is_constant || (hasNoPath && !m.is_crossed);

              return (
                <React.Fragment key={m.mapping_id || i}>
                  <tr className={`mapping-row ${m.is_crossed ? 'row-crossed' : ''}`}>
                    <td
                      style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '11px' }}
                      onClick={() => setExpandedRow(isExpanded ? null : m.mapping_id)}
                      title="Click to view details"
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </td>

                    {/* Segment */}
                    <td>
                      <span className="segment-badge font-mono">
                        {m.destination_segment || m.destination_element?.slice(0, 2) || '—'}
                      </span>
                    </td>

                    {/* Element */}
                    <td>
                      <code className={`element-code ${m.is_crossed ? 'text-crossed' : ''}`}>
                        {m.destination_element || m.mapping_id}
                      </code>
                    </td>

                    {/* Condition with Hover-to-Expand Box */}
                    <td>
                      <HoverExpandBox
                        content={m.conditions}
                        title={`Condition for ${m.destination_element}`}
                        type="condition"
                        isCrossed={m.is_crossed}
                        emptyLabel="—"
                        maxPreviewChars={34}
                        editable={!readOnly}
                        onChange={val => handleListChange(m.mapping_id, 'conditions', val)}
                      />
                    </td>

                    {/* Path with Hover-to-Expand Box */}
                    <td>
                      {hasNoPath ? (
                        <div className="badge-constant-inline" title="No path found; treated as Constant value">
                          <span className="dot-mini constant" /> Constant (No Path)
                        </div>
                      ) : (
                        <HoverExpandBox
                          content={m.source_canonical_path}
                          title={`Canonical Path for ${m.destination_element}`}
                          type="path"
                          isCrossed={m.is_crossed}
                          maxPreviewChars={32}
                          editable={!readOnly}
                          onChange={val => handleCellChange(m.mapping_id, 'source_canonical_path', val)}
                        />
                      )}
                    </td>

                    {/* Constant / Value with Hover-to-Expand Box */}
                    <td>
                      <HoverExpandBox
                        content={
                          m.constants?.length > 0
                            ? m.constants.join(', ')
                            : isConstantEffective
                            ? m.mapping_rule || 'Constant'
                            : '—'
                        }
                        title={`Constant Value for ${m.destination_element}`}
                        type="constant"
                        isConstant={isConstantEffective}
                        isCrossed={m.is_crossed}
                        emptyLabel="—"
                        maxPreviewChars={20}
                        editable={!readOnly}
                        onChange={val => handleListChange(m.mapping_id, 'constants', val)}
                      />
                    </td>

                    {/* Mapping Rule */}
                    <td>
                      <HoverExpandBox
                        content={m.mapping_rule}
                        title={`Rule for ${m.destination_element}`}
                        type="rule"
                        isCrossed={m.is_crossed}
                        maxPreviewChars={26}
                        editable={!readOnly}
                        onChange={val => handleCellChange(m.mapping_id, 'mapping_rule', val)}
                      />
                    </td>

                    {/* Status Pill */}
                    <td>
                      <span className={`status-pill ${statusClass(m.implementation_status, m.is_crossed, isConstantEffective)}`}>
                        {m.is_crossed
                          ? 'Crossed Out'
                          : isConstantEffective
                          ? 'Constant'
                          : (m.implementation_status || 'unresolved').replace(/_/g, ' ')}
                      </span>
                    </td>

                    {/* Action toggle for Crossed / Omit */}
                    {!readOnly && (
                      <td style={{ textAlign: 'center' }}>
                        <button
                          type="button"
                          className={`btn-icon-toggle ${m.is_crossed ? 'active' : ''}`}
                          onClick={() => toggleCrossed(m.mapping_id)}
                          title={m.is_crossed ? 'Include in generation' : 'Cross out / Omit from generation'}
                        >
                          <Ban size={14} />
                        </button>
                      </td>
                    )}
                  </tr>

                  {/* Expanded Row Detail Card */}
                  {isExpanded && (
                    <tr className="expanded-detail-row">
                      <td colSpan={COLUMNS.length + 3} style={{ background: 'var(--bg-surface-3)', padding: '16px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', fontSize: '12px' }}>
                          <div>
                            <strong className="detail-label">Parent Container & Path</strong>
                            <p style={{ marginTop: '4px', fontFamily: 'var(--mono)', color: 'var(--text-secondary)' }}>
                              Segment: <code>{m.parent_segment || m.destination_segment}</code> / Path:{' '}
                              <code>{m.parent_path || 'Root'}</code>
                            </p>
                          </div>
                          <div>
                            <strong className="detail-label">Parent & Element Conditions</strong>
                            <p style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>
                              {m.conditions?.length > 0 ? m.conditions.join('; ') : 'None'}
                            </p>
                          </div>
                          <div>
                            <strong className="detail-label">Generation Behavior</strong>
                            <p style={{ marginTop: '4px', color: 'var(--text-secondary)' }}>
                              {m.is_crossed ? (
                                <span style={{ color: 'var(--red)' }}>
                                  Suppressed / Commented out in generated XSLT (strikethrough)
                                </span>
                              ) : isConstantEffective ? (
                                <span style={{ color: 'var(--blue)' }}>
                                  Emitted as static/constant literal in parent segment
                                </span>
                              ) : (
                                <span style={{ color: 'var(--green)' }}>
                                  Mapped from canonical XPath expression
                                </span>
                              )}
                            </p>
                          </div>
                          {m.related_notes?.length > 0 && (
                            <div style={{ gridColumn: 'span 3' }}>
                              <strong className="detail-label">Original Matrix Notes & Comments</strong>
                              <ul style={{ marginTop: '4px', paddingLeft: '16px', color: 'var(--text-secondary)' }}>
                                {m.related_notes.map((n, ni) => <li key={ni}>{n}</li>)}
                              </ul>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── Sticky Save & Generate Bar ─────────────────────────────── */}
      {!readOnly && (
        <div className="save-bar">
          <div className="info">
            {hasChanges ? (
              <>
                <strong style={{ color: 'var(--amber)' }}>Unsaved modifications</strong> — Save
                changes before generating XSLT
              </>
            ) : (
              <span>All matrix edits synced</span>
            )}
          </div>
          <div className="actions">
            {onSave && (
              <button className="button secondary" onClick={onSave} disabled={!hasChanges || saving}>
                <Save size={14} />
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            )}
            {onGenerate && (
              <button className="button success" onClick={onGenerate} disabled={hasChanges || saving}>
                Generate XSLT →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
