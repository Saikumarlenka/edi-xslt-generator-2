import React, { useState, useMemo, useCallback } from 'react';
import {
  Search, Save, ChevronDown, ChevronUp,
  Filter, Ban, Sparkles, Check, RotateCcw, AlertTriangle,
} from 'lucide-react';

/**
 * Minimal, clean, user-friendly mapping preview table.
 * No intrusive hover popovers.
 * Clear layout: Segment, Element, Condition, Canonical Path, Constant, Rule, Status.
 * Includes loop context and schema suggestions taking parent foreach loops into account.
 */

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

export function HoverTooltip({ title, content, children, className = '' }) {
  const [coords, setCoords] = useState(null);
  const targetRef = React.useRef(null);

  const handleMouseEnter = () => {
    if (targetRef.current && content) {
      const rect = targetRef.current.getBoundingClientRect();
      const spaceAbove = rect.top;
      const showBelow = spaceAbove < 140;
      setCoords({
        top: showBelow ? rect.bottom + 6 : rect.top - 6,
        left: Math.max(12, Math.min(rect.left, window.innerWidth - 490)),
        placement: showBelow ? 'bottom' : 'top',
      });
    }
  };

  const handleMouseLeave = () => {
    setCoords(null);
  };

  return (
    <div
      ref={targetRef}
      className={`hover-tooltip-trigger ${className}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}
      {coords && content && (
        <div
          className={`hover-floating-card ${coords.placement}`}
          style={{
            position: 'fixed',
            top: coords.placement === 'top' ? 'auto' : `${coords.top}px`,
            bottom: coords.placement === 'top' ? `${window.innerHeight - coords.top}px` : 'auto',
            left: `${coords.left}px`,
            zIndex: 99999,
          }}
        >
          {title && <div className="hover-floating-title">{title}</div>}
          <div className="hover-floating-content">{content}</div>
        </div>
      )}
    </div>
  );
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
  const [filterType, setFilterType] = useState('all'); // all | active | constants | conditional | crossed | suggestions
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const [expandedRow, setExpandedRow] = useState(null);

  // Identify non-schema mappings (e.g. @Volume, @VolumeUnitQualifier)
  const notInSchemaMappings = useMemo(() => {
    if (!mappings) return [];
    return mappings.filter(m => m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
      (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier'))));
  }, [mappings]);

  // Statistics
  const stats = useMemo(() => {
    if (!mappings) return { total: 0, constants: 0, crossed: 0, conditional: 0, active: 0, suggestions: 0, notInSchema: 0 };
    const total = mappings.length;
    const crossed = mappings.filter(m => m.is_crossed).length;
    const constants = mappings.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed)).length;
    const conditional = mappings.filter(m => m.conditions && m.conditions.length > 0).length;
    const suggestions = mappings.filter(m => m.suggested_canonical_path && m.suggested_canonical_path !== m.source_document_reference).length;
    const notInSchema = notInSchemaMappings.length;
    return { total, crossed, constants, conditional, active: total - crossed, suggestions, notInSchema };
  }, [mappings, notInSchemaMappings]);

  // Review Points derived from mappings (including schema corrections and non-schema alerts)
  const reviewPoints = useMemo(() => {
    if (!mappings) return [];
    return mappings
      .filter(m => (m.suggested_canonical_path && m.suggested_canonical_path !== m.source_document_reference) ||
        m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
        (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier'))))
      .map(m => {
        const isNonSchema = m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
          (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier')));
        const isApplied = m.source_canonical_path === m.suggested_canonical_path;
        return {
          mapping_id: m.mapping_id,
          destination_segment: m.destination_segment || m.destination_element?.slice(0, 2) || '',
          destination_element: m.destination_element,
          source_document_reference: m.source_document_reference || '—',
          source_canonical_path: m.source_canonical_path || '—',
          suggested_canonical_path: m.suggested_canonical_path || m.source_canonical_path,
          loop_context: m.loop_context || '',
          loop_relative_path: m.loop_relative_path || '',
          suggested_loop_path: m.suggested_loop_path || m.loop_relative_path || '',
          reason: m.path_correction_reason || (isNonSchema ? "Not defined in Canonical Schema (InvoiceCanonicalSchema.xsd). Confirm whether to ignore or keep from matrix." : "Schema-aligned canonical path suggestion"),
          issue_type: isNonSchema ? 'not_in_schema' : (m.path_correction_reason?.toLowerCase().includes('spelling') ? 'spelling' : m.path_correction_reason?.toLowerCase().includes('container') ? 'container' : 'suggestion'),
          isApplied,
          isNonSchema,
          isIgnored: m.is_crossed,
        };
      });
  }, [mappings]);

  // Filter and sort mappings
  const filtered = useMemo(() => {
    if (!mappings) return [];
    let rows = [...mappings];

    if (filterType === 'active') {
      rows = rows.filter(m => !m.is_crossed);
    } else if (filterType === 'constants') {
      rows = rows.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed));
    } else if (filterType === 'conditional') {
      rows = rows.filter(m => m.conditions && m.conditions.length > 0);
    } else if (filterType === 'crossed') {
      rows = rows.filter(m => m.is_crossed);
    } else if (filterType === 'suggestions') {
      rows = rows.filter(m => m.suggested_canonical_path && m.suggested_canonical_path !== m.source_document_reference);
    } else if (filterType === 'not_in_schema') {
      rows = rows.filter(m => m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
        (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier'))));
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(m =>
        Object.values(m).some(v => {
          if (Array.isArray(v)) return v.some(x => String(x).toLowerCase().includes(q));
          return String(v || '').toLowerCase().includes(q);
        })
      );
    }

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
    if (field === 'source_canonical_path' && !value.trim()) {
      item.is_constant = true;
    }
    updated[idx] = item;
    onUpdate(updated);
  }, [mappings, onUpdate]);

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

  // Bulk confirm for all non-schema mappings
  const handleConfirmAllNonSchema = useCallback((shouldIgnore) => {
    if (!onUpdate) return;
    const updated = mappings.map(m => {
      const isNonSchema = m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
        (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier')));
      if (isNonSchema) {
        return {
          ...m,
          is_crossed: shouldIgnore,
          user_confirmation: shouldIgnore ? 'ignore' : 'keep',
          implementation_status: shouldIgnore ? 'excluded_not_in_schema' : 'unresolved',
        };
      }
      return m;
    });
    onUpdate(updated);
  }, [mappings, onUpdate]);

  // Individual toggle for a non-schema mapping
  const handleToggleNonSchema = useCallback((mappingId, shouldIgnore) => {
    if (!onUpdate) return;
    const idx = mappings.findIndex(m => m.mapping_id === mappingId);
    if (idx === -1) return;
    const updated = [...mappings];
    updated[idx] = {
      ...updated[idx],
      is_crossed: shouldIgnore,
      user_confirmation: shouldIgnore ? 'ignore' : 'keep',
      implementation_status: shouldIgnore ? 'excluded_not_in_schema' : 'unresolved',
    };
    onUpdate(updated);
  }, [mappings, onUpdate]);

  if (!mappings?.length) {
    return (
      <div className="empty-state">
        <h3>No mapping data</h3>
        <p>Upload and extract a matrix document to preview and edit mappings.</p>
      </div>
    );
  }

  return (
    <div className="clean-mapping-container">
      {/* ── Minimal Stats & Filter Bar ────────────────────────────── */}
      <div className="clean-toolbar">
        <div className="clean-stats-row">
          <button
            className={`clean-stat-chip ${filterType === 'all' ? 'active' : ''}`}
            onClick={() => setFilterType('all')}
          >
            <span className="count">{stats.total}</span>
            <span className="label">Total</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'active' ? 'active' : ''}`}
            onClick={() => setFilterType('active')}
          >
            <span className="count active-count">{stats.active}</span>
            <span className="label">Active</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'constants' ? 'active' : ''}`}
            onClick={() => setFilterType('constants')}
          >
            <span className="count const-count">{stats.constants}</span>
            <span className="label">Constants</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'conditional' ? 'active' : ''}`}
            onClick={() => setFilterType('conditional')}
          >
            <span className="count cond-count">{stats.conditional}</span>
            <span className="label">Conditional</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'crossed' ? 'active' : ''}`}
            onClick={() => setFilterType('crossed')}
          >
            <span className="count crossed-count">{stats.crossed}</span>
            <span className="label">Excluded</span>
          </button>
          {stats.suggestions > 0 && (
            <button
              className={`clean-stat-chip highlight ${filterType === 'suggestions' ? 'active' : ''}`}
              onClick={() => setFilterType('suggestions')}
            >
              <Sparkles size={13} />
              <span className="count">{stats.suggestions}</span>
              <span className="label">Suggestions</span>
            </button>
          )}
          {stats.notInSchema > 0 && (
            <button
              className={`clean-stat-chip not-in-schema ${filterType === 'not_in_schema' ? 'active' : ''}`}
              onClick={() => setFilterType('not_in_schema')}
              title="Filter to elements not present in Canonical Schema (e.g. @Volume, @VolumeUnitQualifier)"
            >
              <AlertTriangle size={13} style={{ color: '#fbbf24' }} />
              <span className="count not-in-schema-count">{stats.notInSchema}</span>
              <span className="label">Not in Schema</span>
            </button>
          )}
        </div>

        <div className="clean-search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search elements, paths, rules…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* ── Non-Schema Attributes Confirmation Alert Card ───────────── */}
      {notInSchemaMappings.length > 0 && (
        <div className="schema-confirmation-card">
          <div className="card-left">
            <div className="card-badge">
              <AlertTriangle size={15} /> Non-Schema Attributes Detected ({notInSchemaMappings.length})
            </div>
            <div className="card-desc">
              The matrix maps attributes or paths that are not defined in the Canonical Schema (<code>InvoiceCanonicalSchema.xsd</code>), such as{' '}
              <strong>{notInSchemaMappings.map(m => m.destination_element + (m.source_canonical_path?.includes('@') ? ' (@' + m.source_canonical_path.split('@')[1] + ')' : (m.source_canonical_path ? ' (' + m.source_canonical_path.split('/').pop() + ')' : ''))).join(', ')}</strong>.
              Please confirm whether to <strong>Ignore (Omit)</strong> these mappings from the generated XSLT or <strong>Keep as is</strong> from the extracted matrix:
            </div>
          </div>
          <div className="card-actions">
            <button
              type="button"
              className="button small-btn warn"
              onClick={() => handleConfirmAllNonSchema(true)}
              title="Omit non-schema attributes from the generated XSLT"
            >
              <Ban size={13} /> Ignore All ({notInSchemaMappings.length})
            </button>
            <button
              type="button"
              className="button small-btn success"
              onClick={() => handleConfirmAllNonSchema(false)}
              title="Keep non-schema attributes in generated XSLT as extracted from matrix"
            >
              <Check size={13} /> Keep All from Matrix
            </button>
          </div>
        </div>
      )}

      {/* ── Clean Table ────────────────────────────────────────────── */}
      <div className="clean-table-card">
        <table className="clean-table">
          <thead>
            <tr>
              <th style={{ width: '36px' }}></th>
              <th
                style={{ width: '80px', cursor: 'pointer' }}
                onClick={() => toggleSort('destination_segment')}
              >
                Seg {sortCol === 'destination_segment' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th
                style={{ width: '90px', cursor: 'pointer' }}
                onClick={() => toggleSort('destination_element')}
              >
                Elem {sortCol === 'destination_element' && (sortDir === 'asc' ? '↑' : '↓')}
              </th>
              <th style={{ width: '220px' }}>Condition / Loop</th>
              <th style={{ width: '280px' }}>Canonical Path / Context</th>
              <th style={{ width: '130px' }}>Constant Value</th>
              <th>Mapping Rule</th>
              <th style={{ width: '110px' }}>Status</th>
              {!readOnly && <th style={{ width: '60px', textAlign: 'center' }}>Omit</th>}
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => {
              const isExpanded = expandedRow === m.mapping_id;
              const hasNoPath = !m.source_canonical_path || m.source_canonical_path === 'unknown';
              const isConstantEffective = m.is_constant || (hasNoPath && !m.is_crossed);
              const hasSuggestion = m.suggested_canonical_path && m.suggested_canonical_path !== m.source_document_reference;
              const isNonSchema = m.is_not_in_schema || m.schema_validation_status === 'not_in_schema' ||
                (m.source_canonical_path && (m.source_canonical_path.includes('@Volume') || m.source_canonical_path.includes('@VolumeUnitQualifier')));

              return (
                <React.Fragment key={m.mapping_id || i}>
                  <tr className={`clean-row ${m.is_crossed ? 'is-crossed' : ''}`}>
                    <td
                      className="expand-cell"
                      onClick={() => setExpandedRow(isExpanded ? null : m.mapping_id)}
                      title="Toggle row details"
                    >
                      {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </td>

                    {/* Segment */}
                    <td>
                      <span className="clean-badge segment">
                        {m.destination_segment || m.destination_element?.slice(0, 2) || '—'}
                      </span>
                    </td>

                    {/* Element */}
                    <td>
                      <code className={`clean-element ${m.is_crossed ? 'text-crossed' : ''}`}>
                        {m.destination_element || m.mapping_id}
                      </code>
                      {isNonSchema && (
                        <span className="clean-badge not-in-schema" title="Attribute not defined in InvoiceCanonicalSchema.xsd">
                          ⚠️ Not in Schema
                        </span>
                      )}
                    </td>

                    {/* Condition */}
                    <td>
                      {m.conditions?.length > 0 ? (
                        <HoverTooltip
                          title="Active Condition / Loop Filter"
                          content={
                            <div>
                              <div className="tooltip-main-text">{m.conditions.join('\n')}</div>
                              {m.parent_condition && (
                                <div className="tooltip-sub-info">
                                  <span className="tooltip-sub-label">Parent Container:</span> {m.parent_condition}
                                </div>
                              )}
                            </div>
                          }
                        >
                          <div className="clean-cond-text" title={m.conditions.join('; ')}>
                            {m.conditions[0]}
                            {m.conditions.length > 1 && <span className="extra-tag">+{m.conditions.length - 1}</span>}
                          </div>
                        </HoverTooltip>
                      ) : (
                        <span className="dim-text">—</span>
                      )}
                    </td>

                    {/* Canonical Path */}
                    <td>
                      {hasNoPath ? (
                        <span className="clean-badge constant-label">Constant (No Path)</span>
                      ) : (
                        <HoverTooltip
                          title="Canonical Schema Path & Context"
                          content={
                            <div>
                              <div className="tooltip-main-text font-mono">{m.source_canonical_path}</div>
                              {isNonSchema && (
                                <div className="tooltip-sub-info schema-warn-box">
                                  <span className="tooltip-sub-label">⚠️ Not in Canonical Schema:</span>
                                  <div>This attribute is not part of InvoiceCanonicalSchema.xsd under LineItemQuantityAndWeight. You can confirm whether to ignore (omit) or keep it from matrix.</div>
                                </div>
                              )}
                              {m.loop_context && (
                                <div className="tooltip-sub-info">
                                  <span className="tooltip-sub-label">Enclosing Loop:</span> {m.loop_context}
                                  {m.loop_relative_path && (
                                    <div><span className="tooltip-sub-label">Relative XPath:</span> {m.loop_relative_path}</div>
                                  )}
                                </div>
                              )}
                              {m.source_document_reference && m.source_document_reference !== m.source_canonical_path && (
                                <div className="tooltip-sub-info">
                                  <span className="tooltip-sub-label">Matrix Raw:</span> {m.source_document_reference}
                                </div>
                              )}
                              {m.path_correction_reason && (
                                <div className="tooltip-sub-info schema-note">
                                  <span className="tooltip-sub-label">Schema Suggestion:</span> {m.path_correction_reason}
                                </div>
                              )}
                            </div>
                          }
                        >
                          <div className="path-cell-wrap">
                            {!readOnly ? (
                              <input
                                className="clean-inline-input font-mono"
                                value={m.source_canonical_path}
                                onChange={e => handleCellChange(m.mapping_id, 'source_canonical_path', e.target.value)}
                                title={m.source_canonical_path}
                              />
                            ) : (
                              <span className="font-mono path-text" title={m.source_canonical_path}>
                                {m.source_canonical_path}
                              </span>
                            )}

                            {m.loop_context && m.loop_context !== 'Header' && m.loop_context !== 'Summary' && (
                              <span className="loop-indicator" title={`Evaluated inside loop: ${m.loop_context}`}>
                                in {m.loop_context.split('/').pop()}
                              </span>
                            )}

                            {hasSuggestion && (
                              <span
                                className={`suggestion-pill ${m.source_canonical_path === m.suggested_canonical_path ? 'applied' : 'custom'}`}
                                title={`Matrix: ${m.source_document_reference}\nSuggested: ${m.suggested_canonical_path}\nReason: ${m.path_correction_reason || 'Canonical alignment'}`}
                              >
                                <Sparkles size={10} />
                                {m.source_canonical_path === m.suggested_canonical_path ? 'Corrected' : 'Suggestion'}
                              </span>
                            )}
                          </div>
                        </HoverTooltip>
                      )}
                    </td>

                    {/* Constant */}
                    <td>
                      {isConstantEffective ? (
                        <HoverTooltip
                          title="Constant Value"
                          content={
                            <div className="tooltip-main-text font-mono">
                              {m.constants?.join(', ') || m.mapping_rule || 'Constant'}
                            </div>
                          }
                        >
                          {!readOnly ? (
                            <input
                              className="clean-inline-input font-mono"
                              value={m.constants?.join(', ') || m.mapping_rule || ''}
                              onChange={e => handleCellChange(m.mapping_id, 'constants', [e.target.value])}
                              placeholder="Value"
                              title={m.constants?.join(', ') || m.mapping_rule}
                            />
                          ) : (
                            <span className="font-mono">{m.constants?.join(', ') || m.mapping_rule || 'Constant'}</span>
                          )}
                        </HoverTooltip>
                      ) : (
                        <span className="dim-text">—</span>
                      )}
                    </td>

                    {/* Mapping Rule */}
                    <td>
                      <HoverTooltip
                        title="Matrix Mapping Rule & Logic"
                        content={
                          <div>
                            <div className="tooltip-main-text">{m.mapping_rule || '—'}</div>
                            {m.transformations?.length > 0 && (
                              <div className="tooltip-sub-info">
                                <span className="tooltip-sub-label">Transformations:</span> {m.transformations.join(', ')}
                              </div>
                            )}
                          </div>
                        }
                      >
                        {!readOnly ? (
                          <input
                            className="clean-inline-input"
                            value={m.mapping_rule || ''}
                            onChange={e => handleCellChange(m.mapping_id, 'mapping_rule', e.target.value)}
                            placeholder="Mapping note"
                            title={m.mapping_rule}
                          />
                        ) : (
                          <span className="rule-text" title={m.mapping_rule}>
                            {m.mapping_rule || '—'}
                          </span>
                        )}
                      </HoverTooltip>
                    </td>

                    {/* Status */}
                    <td>
                      {isNonSchema ? (
                        <span className={`clean-status ${m.is_crossed ? 'crossed' : 'warning-kept'}`} title={m.is_crossed ? "Ignored: omitted from generated XSLT" : "Kept: will be generated into XSLT per matrix"}>
                          {m.is_crossed ? 'Ignored' : 'Kept (Matrix)'}
                        </span>
                      ) : (
                        <span className={`clean-status ${statusClass(m.implementation_status, m.is_crossed, isConstantEffective)}`}>
                          {m.is_crossed ? 'Excluded' : isConstantEffective ? 'Constant' : 'Active'}
                        </span>
                      )}
                    </td>

                    {/* Omit Toggle */}
                    {!readOnly && (
                      <td style={{ textAlign: 'center' }}>
                        {isNonSchema ? (
                          <button
                            type="button"
                            className={`clean-toggle-btn ${m.is_crossed ? 'active' : ''}`}
                            onClick={() => handleToggleNonSchema(m.mapping_id, !m.is_crossed)}
                            title={m.is_crossed ? 'Click to Keep this mapping from matrix' : 'Click to Ignore (Omit) this non-schema mapping'}
                          >
                            {m.is_crossed ? <Check size={13} style={{ color: '#10b981' }} /> : <Ban size={13} />}
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={`clean-toggle-btn ${m.is_crossed ? 'active' : ''}`}
                            onClick={() => toggleCrossed(m.mapping_id)}
                            title={m.is_crossed ? 'Restore to active generation' : 'Exclude / comment out'}
                          >
                            <Ban size={13} />
                          </button>
                        )}
                      </td>
                    )}
                  </tr>

                  {/* Clean Inline Detail Card on Expand */}
                  {isExpanded && (
                    <tr className="clean-expand-row">
                      <td colSpan={9}>
                        <div className="clean-expand-box">
                          <div className="expand-grid">
                            <div>
                              <span className="expand-title">Raw Document Text</span>
                              <code>{m.source_document_reference || '—'}</code>
                            </div>
                            <div>
                              <span className="expand-title">Canonical Full Path</span>
                              <code>{m.source_canonical_path || 'None'}</code>
                            </div>
                            <div>
                              <span className="expand-title">Enclosing Loop Context</span>
                              <code>{m.loop_context || m.parent_path || 'Root'}</code>
                            </div>
                            {m.loop_relative_path && (
                              <div>
                                <span className="expand-title">Loop-Relative XPath</span>
                                <code>{m.loop_relative_path}</code>
                              </div>
                            )}
                            {m.conditions?.length > 0 && (
                              <div style={{ gridColumn: 'span 2' }}>
                                <span className="expand-title">Conditions</span>
                                <span>{m.conditions.join('; ')}</span>
                              </div>
                            )}
                            {m.path_correction_reason && (
                              <div style={{ gridColumn: 'span 2' }}>
                                <span className="expand-title">Schema Diagnostic</span>
                                <span className="reason-text">{m.path_correction_reason}</span>
                              </div>
                            )}
                          </div>
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

      {/* ── Schema Review Points & Suggestions Section ────────────── */}
      {reviewPoints.length > 0 && (
        <div className="clean-suggestions-section">
          <div className="suggestions-header">
            <div>
              <h3>
                <Sparkles size={16} /> Schema Path Suggestions ({reviewPoints.length})
              </h3>
              <p>
                Spelling or container variations detected against the canonical schema and test file. Loop contexts are verified.
              </p>
            </div>
          </div>

          <div className="suggestions-list">
            {reviewPoints.map(rp => (
              <div
                key={rp.mapping_id}
                className={`suggestion-item ${rp.isNonSchema ? (rp.isIgnored ? 'ignored' : 'pending-warn') : (rp.isApplied ? 'applied' : 'custom')}`}
              >
                <div className="sugg-left">
                  <div className="sugg-header">
                    <span className="clean-badge segment">{rp.destination_segment}</span>
                    <code className="clean-element">{rp.destination_element}</code>
                    <span className={`issue-type-tag ${rp.isNonSchema ? 'warn' : ''}`}>{rp.issue_type}</span>
                    {rp.isNonSchema && (
                      <span className={`clean-badge ${rp.isIgnored ? 'crossed' : 'active'}`} style={{ marginLeft: '6px', fontSize: '11px' }}>
                        {rp.isIgnored ? 'Ignored (Omitted from XSLT)' : 'Kept (Will Generate into XSLT)'}
                      </span>
                    )}
                  </div>
                  <div className="sugg-details">
                    <div>
                      <span className="field-lbl">Matrix Raw:</span>
                      <code>{rp.source_document_reference}</code>
                    </div>
                    <div>
                      <span className="field-lbl">Schema Path:</span>
                      <code>{rp.suggested_canonical_path}</code>
                    </div>
                    {rp.loop_context && rp.loop_context !== 'Header' && (
                      <div>
                        <span className="field-lbl">Enclosing Loop:</span>
                        <span className="loop-highlight">{rp.loop_context}</span>
                        {rp.suggested_loop_path && (
                          <span className="loop-xpath"> (Relative XPath: <code>{rp.suggested_loop_path}</code>)</span>
                        )}
                      </div>
                    )}
                    {rp.reason && <p className="sugg-reason">{rp.reason}</p>}
                  </div>
                </div>

                {!readOnly && (
                  <div className="sugg-action">
                    {rp.isNonSchema ? (
                      <div style={{ display: 'flex', gap: '6px' }}>
                        {!rp.isIgnored ? (
                          <button
                            type="button"
                            className="button secondary sm"
                            style={{ color: '#f59e0b', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                            onClick={() => handleToggleNonSchema(rp.mapping_id, true)}
                            title="Omit this non-schema mapping from XSLT generation"
                          >
                            <Ban size={13} /> Ignore (Omit)
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="button primary sm"
                            style={{ backgroundColor: '#10b981', borderColor: '#10b981' }}
                            onClick={() => handleToggleNonSchema(rp.mapping_id, false)}
                            title="Keep this mapping and generate into XSLT per matrix"
                          >
                            <Check size={13} /> Keep from Matrix
                          </button>
                        )}
                      </div>
                    ) : !rp.isApplied ? (
                      <button
                        type="button"
                        className="button primary sm"
                        onClick={() => handleCellChange(rp.mapping_id, 'source_canonical_path', rp.suggested_canonical_path)}
                      >
                        <Check size={13} /> Apply Suggestion
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="button secondary sm"
                        onClick={() => handleCellChange(rp.mapping_id, 'source_canonical_path', rp.source_document_reference)}
                        title="Revert back to exact text from matrix"
                      >
                        <RotateCcw size={13} /> Revert to Matrix
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Clean Sticky Action Bar ─────────────────────────────────── */}
      {!readOnly && (
        <div className="clean-action-bar">
          <div className="bar-status">
            {hasChanges ? (
              <span className="status-unsaved">● Unsaved edits ready to be applied</span>
            ) : (
              <span className="status-synced">✓ Mappings synchronized with matrix</span>
            )}
          </div>
          <div className="bar-buttons">
            {onSave && (
              <button
                className="button secondary"
                onClick={onSave}
                disabled={!hasChanges || saving}
              >
                <Save size={14} />
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            )}
            {onGenerate && (
              <button
                className="button primary"
                onClick={onGenerate}
                disabled={hasChanges || saving}
              >
                Generate XSLT →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
