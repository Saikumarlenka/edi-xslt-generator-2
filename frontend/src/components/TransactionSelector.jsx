import React from 'react';

export default function TransactionSelector({ value, onChange }) {
  return (
    <div className="segmented">
      <button
        className={value === '210' ? 'active' : ''}
        onClick={() => onChange('210')}
      >
        EDI 210 · Freight Invoice
      </button>
      <button
        className={value === '214' ? 'active' : ''}
        onClick={() => onChange('214')}
      >
        EDI 214 · Shipment Status
      </button>
    </div>
  );
}
