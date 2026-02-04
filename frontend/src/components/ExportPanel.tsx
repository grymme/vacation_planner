import React, { useState } from 'react';
import { exportApi } from '../api/vacation';
import './ExportPanel.css';

export default function ExportPanel() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [status, setStatus] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const handleExportCSV = async () => {
    setIsExporting(true);
    try {
      exportApi.exportCSV({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        status: status || undefined
      });
    } catch (error) {
      console.error('CSV export failed:', error);
      alert('Failed to export CSV');
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportXLSX = async () => {
    setIsExporting(true);
    try {
      exportApi.exportXLSX({
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        status: status || undefined
      });
    } catch (error) {
      console.error('XLSX export failed:', error);
      alert('Failed to export XLSX');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="export-panel">
      <h3>Export Options</h3>
      
      <div className="export-filters">
        <div className="form-group">
          <label>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>Status</label>
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="pending">Pending</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>
      
      <div className="export-buttons">
        <button onClick={handleExportCSV} disabled={isExporting} className="btn btn-outline">
          📄 Export CSV
        </button>
        <button onClick={handleExportXLSX} disabled={isExporting} className="btn btn-outline">
          📊 Export XLSX
        </button>
      </div>
    </div>
  );
}
