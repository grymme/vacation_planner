import React from 'react';
import Calendar from '../components/Calendar';

export default function ApprovalsPage() {
  return (
    <div className="page">
      <h1>Pending Approvals</h1>
      <Calendar viewMode="manager" onRequestCreate={() => window.location.reload()} />
    </div>
  );
}
