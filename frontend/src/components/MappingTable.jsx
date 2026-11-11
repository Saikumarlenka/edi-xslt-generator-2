import React, { useState, useMemo } from 'react';
import { Search, Sparkles } from 'lucide-react';
import { HoverTooltip } from './MappingPreview';

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

export default function MappingTable({ spec }) {
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState('all');

  const mappings = spec?.mappings || [];

  const filtered = useMemo(() => {
    let rows = [...mappings];
    if (filterType === 'active') {
      rows = rows.filter(m => !m.is_crossed);
    } else if (filterType === 'constants') {
      rows = rows.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed));
    } else if (filterType === 'conditional') {
      rows = rows.filter(m => m.conditions && m.conditions.length > 0);
    } else if (filterType === 'crossed') {
      rows = rows.filter(m => m.is_crossed);
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
    return rows;
  }, [mappings, filterType, search]);

  if (!mappings.length) {
    return (
      <div className="empty-state">
        <h3>No mapping data</h3>
        <p>Mapping specification will appear when the matrix has been extracted.</p>
      </div>
    );
  }

  const crossedCount = mappings.filter(m => m.is_crossed).length;
  const constCount = mappings.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed)).length;
  const condCount = mappings.filter(m => m.conditions && m.conditions.length > 0).length;

  return (
    <div className="clean-mapping-container">
      <div className="clean-toolbar">
        <div className="clean-stats-row">
          <button
            className={`clean-stat-chip ${filterType === 'all' ? 'active' : ''}`}
            onClick={() => setFilterType('all')}
          >
            <span className="count">{mappings.length}</span>
            <span className="label">Total</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'active' ? 'active' : ''}`}
            onClick={() => setFilterType('active')}
          >
            <span className="count active-count">{mappings.length - crossedCount}</span>
            <span className="label">Active</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'constants' ? 'active' : ''}`}
            onClick={() => setFilterType('constants')}
          >
            <span className="count const-count">{constCount}</span>
            <span className="label">Constants</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'conditional' ? 'active' : ''}`}
            onClick={() => setFilterType('conditional')}
          >
            <span className="count cond-count">{condCount}</span>
            <span className="label">Conditional</span>
          </button>
          <button
            className={`clean-stat-chip ${filterType === 'crossed' ? 'active' : ''}`}
            onClick={() => setFilterType('crossed')}
          >
            <span className="count crossed-count">{crossedCount}</span>
            <span className="label">Excluded</span>
          </button>
        </div>

        <div className="clean-search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search table…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="clean-table-card">
        <table className="clean-table">
          <thead>
            <tr>
              <th style={{ width: '80px' }}>Seg</th>
              <th style={{ width: '90px' }}>Elem</th>
              <th style={{ width: '220px' }}>Condition / Loop</th>
              <th style={{ width: '280px' }}>Canonical Path</th>
              <th style={{ width: '130px' }}>Constant Value</th>
              <th>Mapping Rule</th>
              <th style={{ width: '110px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => {
              const hasNoPath = !m.source_canonical_path || m.source_canonical_path === 'unknown';
              const isConstantEffective = m.is_constant || (hasNoPath && !m.is_crossed);
              const hasSuggestion = m.suggested_canonical_path && m.suggested_canonical_path !== m.source_document_reference;

              return (
                <tr key={m.mapping_id || i} className={`clean-row ${m.is_crossed ? 'is-crossed' : ''}`}>
                  <td>
                    <span className="clean-badge segment">
                      {m.destination_segment || m.destination_element?.slice(0, 2) || '—'}
                    </span>
                  </td>
                  <td>
                    <code className={`clean-element ${m.is_crossed ? 'text-crossed' : ''}`}>
                      {m.destination_element || m.mapping_id}
                    </code>
                  </td>
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
                        <span className="clean-cond-text" title={m.conditions.join('; ')}>
                          {m.conditions.join('; ')}
                        </span>
                      </HoverTooltip>
                    ) : (
                      <span className="dim-text">—</span>
                    )}
                  </td>
                  <td>
                    {hasNoPath ? (
                      <span className="clean-badge constant-label">Constant (No Path)</span>
                    ) : (
                      <HoverTooltip
                        title="Canonical Schema Path & Context"
                        content={
                          <div>
                            <div className="tooltip-main-text font-mono">{m.source_canonical_path}</div>
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
                          <span className="font-mono path-text" title={m.source_canonical_path}>
                            {m.source_canonical_path}
                          </span>
                          {m.loop_context && m.loop_context !== 'Header' && m.loop_context !== 'Summary' && (
                            <span className="loop-indicator">in {m.loop_context.split('/').pop()}</span>
                          )}
                          {hasSuggestion && (
                            <span className="suggestion-pill applied" title={m.path_correction_reason}>
                              <Sparkles size={10} /> Corrected
                            </span>
                          )}
                        </div>
                      </HoverTooltip>
                    )}
                  </td>
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
                        <span className="font-mono">{m.constants?.join(', ') || m.mapping_rule || 'Constant'}</span>
                      </HoverTooltip>
                    ) : (
                      <span className="dim-text">—</span>
                    )}
                  </td>
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
                      <span className="rule-text" title={m.mapping_rule}>
                        {m.mapping_rule || '—'}
                      </span>
                    </HoverTooltip>
                  </td>
                  <td>
                    <span className={`clean-status ${statusClass(m.implementation_status, m.is_crossed, isConstantEffective)}`}>
                      {m.is_crossed ? 'Excluded' : isConstantEffective ? 'Constant' : 'Active'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
