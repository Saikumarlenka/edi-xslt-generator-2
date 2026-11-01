import React, { useState, useMemo } from 'react';
import { Table, Search, Filter } from 'lucide-react';
import HoverExpandBox from './HoverExpandBox';

/**
 * Enhanced mapping table shown in the Review & Results tab.
 * Displays: Segment, Element, Condition, Path, Constants/Values, Rule, Status.
 * Hovering on any box expands it for full visibility.
 * Clear visual distinction for Constants and Crossed-out/Suppressed items.
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
        <div className="icon"><Table size={24} /></div>
        <h3>No mapping data</h3>
        <p>Mapping specification will appear when the matrix has been extracted.</p>
      </div>
    );
  }

  const crossedCount = mappings.filter(m => m.is_crossed).length;
  const constCount = mappings.filter(m => m.is_constant || (!m.source_canonical_path && !m.is_crossed)).length;
  const condCount = mappings.filter(m => m.conditions && m.conditions.length > 0).length;

  return (
    <div className="mapping-table-review">
      {/* Sub-header & Filters */}
      <div className="mapping-toolbar" style={{ marginBottom: '12px' }}>
        <div className="left">
          <div className="filter-chips-bar" style={{ margin: 0, padding: 0, border: 'none' }}>
            <button
              className={`filter-chip ${filterType === 'all' ? 'selected' : ''}`}
              onClick={() => setFilterType('all')}
            >
              All ({mappings.length})
            </button>
            <button
              className={`filter-chip ${filterType === 'active' ? 'selected' : ''}`}
              onClick={() => setFilterType('active')}
            >
              Active Output ({mappings.length - crossedCount})
            </button>
            <button
              className={`filter-chip ${filterType === 'constants' ? 'selected' : ''}`}
              onClick={() => setFilterType('constants')}
            >
              Constants ({constCount})
            </button>
            <button
              className={`filter-chip ${filterType === 'conditional' ? 'selected' : ''}`}
              onClick={() => setFilterType('conditional')}
            >
              Conditional ({condCount})
            </button>
            <button
              className={`filter-chip ${filterType === 'crossed' ? 'selected' : ''}`}
              onClick={() => setFilterType('crossed')}
            >
              Crossed Out ({crossedCount})
            </button>
          </div>
        </div>
        <div className="right">
          <div className="search-box">
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Search table…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="table-wrap" style={{ maxHeight: '550px', overflowY: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th style={{ width: '80px' }}>Segment</th>
              <th style={{ width: '90px' }}>Element</th>
              <th style={{ width: '220px' }}>Condition</th>
              <th style={{ width: '230px' }}>Canonical Path</th>
              <th style={{ width: '130px' }}>Constant / Value</th>
              <th style={{ width: '180px' }}>Rule</th>
              <th style={{ width: '110px' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((m, i) => {
              const hasNoPath = !m.source_canonical_path || m.source_canonical_path === 'unknown';
              const isConstantEffective = m.is_constant || (hasNoPath && !m.is_crossed);

              return (
                <tr key={m.mapping_id || i} className={m.is_crossed ? 'row-crossed' : ''}>
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
                      maxPreviewChars={34}
                    />
                  </td>

                  {/* Path with Hover-to-Expand Box */}
                  <td>
                    {hasNoPath ? (
                      <div className="badge-constant-inline" title="No path; treated as constant static value">
                        <span className="dot-mini constant" /> Constant (No Path)
                      </div>
                    ) : (
                      <HoverExpandBox
                        content={m.source_canonical_path}
                        title={`Canonical Path for ${m.destination_element}`}
                        type="path"
                        isCrossed={m.is_crossed}
                        maxPreviewChars={32}
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
                      maxPreviewChars={20}
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
                    />
                  </td>

                  {/* Status */}
                  <td>
                    <span className={`status-pill ${statusClass(m.implementation_status, m.is_crossed, isConstantEffective)}`}>
                      {m.is_crossed
                        ? 'Crossed Out'
                        : isConstantEffective
                        ? 'Constant'
                        : (m.implementation_status || 'unresolved').replace(/_/g, ' ')}
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
