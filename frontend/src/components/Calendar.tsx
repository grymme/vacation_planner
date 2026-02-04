import React, { useState, useEffect, useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import { vacationApi, UserResponse, VacationRequest } from '../api/vacation';
import { teamsApi, vacationBalanceApi, VacationBalance } from '../api/vacation';
import { useAuth } from '../context/AuthContext';
import ExportPanel from './ExportPanel';
import './Calendar.css';

interface CalendarProps {
  onRequestCreate?: () => void;
  viewMode?: 'user' | 'manager';
}

export default function Calendar({ onRequestCreate, viewMode = 'user' }: CalendarProps) {
  const calendarRef = useRef<FullCalendar>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [vacationRequests, setVacationRequests] = useState<VacationRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedRequest, setSelectedRequest] = useState<VacationRequest | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [showActionModal, setShowActionModal] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [vacationBalance, setVacationBalance] = useState<VacationBalance | null>(null);
  
  const { user } = useAuth();
  const [newRequest, setNewRequest] = useState({
    start_date: '',
    end_date: '',
    vacation_type: 'annual',
    reason: '',
    team_id: ''
  });
  const [actionComment, setActionComment] = useState('');
  const [actionType, setActionType] = useState<'approve' | 'reject'>('approve');

  useEffect(() => {
    fetchData();
  }, [viewMode]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [requestsRes, teamsRes] = await Promise.all([
        viewMode === 'manager' 
          ? vacationApi.getPendingRequests()
          : vacationApi.getMyRequests(),
        teamsApi.getManagedTeams()
      ]);
      
      setVacationRequests(requestsRes.data);
      setTeams(teamsRes.data);
      
      // Fetch vacation balance for user view
      if (viewMode === 'user') {
        try {
          const balance = await vacationBalanceApi.getVacationBalance();
          setVacationBalance(balance);
        } catch (err) {
          console.warn('Could not fetch vacation balance:', err);
        }
      }
      
      // Transform to calendar events with period-aware coloring
      const calendarEvents = requestsRes.data.map((vr: VacationRequest) => ({
        id: vr.id,
        title: `${vr.user.first_name} ${vr.user.last_name} (${vr.vacation_type})`,
        start: vr.start_date,
        end: vr.end_date,
        backgroundColor: getStatusColor(vr.status),
        borderColor: getStatusColor(vr.status),
        extendedProps: { 
          vacationRequest: vr,
          periodInfo: vacationBalance?.vacation_period?.name || null
        }
      }));
      
      setEvents(calendarEvents);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return '#22c55e';
      case 'pending': return '#f59e0b';
      case 'rejected': return '#ef4444';
      case 'cancelled': return '#6b7280';
      default: return '#3b82f6';
    }
  };

  const getPeriodColor = (status: string): string => {
    // Returns slightly different shades based on status for period differentiation
    switch (status) {
      case 'approved': return '#16a34a';
      case 'pending': return '#d97706';
      case 'rejected': return '#dc2626';
      case 'cancelled': return '#4b5563';
      default: return '#2563eb';
    }
  };

  const handleDateSelect = (selectInfo: any) => {
    setNewRequest({
      ...newRequest,
      start_date: selectInfo.startStr.split('T')[0],
      end_date: selectInfo.endStr.split('T')[0]
    });
    setShowModal(true);
  };

  const handleEventClick = (clickInfo: any) => {
    const vr = clickInfo.event.extendedProps.vacationRequest;
    setSelectedRequest(vr);
    setShowModal(true);
  };

  const handleCreateRequest = async () => {
    try {
      await vacationApi.createRequest(newRequest);
      setShowModal(false);
      setNewRequest({ start_date: '', end_date: '', vacation_type: 'annual', reason: '', team_id: '' });
      fetchData();
      onRequestCreate?.();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to create request');
    }
  };

  const handleApproveReject = async (action: 'approve' | 'reject') => {
    if (!selectedRequest) return;
    
    try {
      await vacationApi.approveRequest(selectedRequest.id, { action, comment: actionComment });
      setShowActionModal(false);
      setActionComment('');
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to process request');
    }
  };

  const handleCancelRequest = async () => {
    if (!selectedRequest) return;
    
    try {
      await vacationApi.cancelRequest(selectedRequest.id);
      setShowModal(false);
      fetchData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to cancel request');
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'approved': return 'Approved';
      case 'pending': return 'Pending';
      case 'rejected': return 'Rejected';
      case 'cancelled': return 'Cancelled';
      default: return status;
    }
  };

  return (
    <div className="calendar-wrapper">
      <ExportPanel onExportPNG={fetchData} />
      <div id="calendar-container" className="calendar-container">
        {isLoading ? (
          <div className="calendar-loading">Loading calendar...</div>
        ) : (
          <>
            <FullCalendar
              ref={calendarRef}
              plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
              initialView="dayGridMonth"
              headerToolbar={{
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
              }}
              selectable={viewMode === 'user'}
              selectMirror={true}
              dayMaxEvents={true}
              events={events}
              select={handleDateSelect}
              eventClick={handleEventClick}
              height="auto"
            />
            
            {/* Legend */}
            <div className="calendar-legend">
              <span className="legend-item"><span className="legend-color approved"></span> Approved</span>
              <span className="legend-item"><span className="legend-color pending"></span> Pending</span>
              <span className="legend-item"><span className="legend-color rejected"></span> Rejected</span>
              <span className="legend-item"><span className="legend-color cancelled"></span> Cancelled</span>
            </div>
          </>
        )}
      </div>
      
      {/* Create/View Request Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedRequest ? 'Vacation Request' : 'New Vacation Request'}</h3>
              <button className="modal-close" onClick={() => setShowModal(false)}>×</button>
            </div>
            
            <div className="modal-body">
              {selectedRequest ? (
                <>
                  <div className="request-detail">
                    <label>Employee:</label>
                    <span>{selectedRequest.user.first_name} {selectedRequest.user.last_name}</span>
                  </div>
                  <div className="request-detail">
                    <label>Status:</label>
                    <span className={`status-badge status-${selectedRequest.status}`}>
                      {getStatusText(selectedRequest.status)}
                    </span>
                  </div>
                  <div className="request-detail">
                    <label>Type:</label>
                    <span>{selectedRequest.vacation_type}</span>
                  </div>
                  <div className="request-detail">
                    <label>Dates:</label>
                    <span>{selectedRequest.start_date} to {selectedRequest.end_date}</span>
                  </div>
                  {selectedRequest.reason && (
                    <div className="request-detail">
                      <label>Reason:</label>
                      <span>{selectedRequest.reason}</span>
                    </div>
                  )}
                  
                  {/* Period info (would be populated from backend if available) */}
                  {selectedRequest.vacation_type && (
                    <div className="request-detail">
                      <label>Vacation Year:</label>
                      <span>{vacationBalance?.vacation_period?.name || 'Current Period'}</span>
                    </div>
                  )}
                  
                  {/* Manager actions for pending requests */}
                  {viewMode === 'manager' && selectedRequest.status === 'pending' && (
                    <div className="manager-actions">
                      <button 
                        className="btn btn-success"
                        onClick={() => {
                          setActionType('approve');
                          setShowActionModal(true);
                        }}
                      >
                        Approve
                      </button>
                      <button 
                        className="btn btn-danger"
                        onClick={() => {
                          setActionType('reject');
                          setShowActionModal(true);
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  )}
                  
                  {/* User cancel for own pending requests */}
                  {viewMode === 'user' && selectedRequest.status === 'pending' && (
                    <button className="btn btn-danger" onClick={handleCancelRequest}>
                      Cancel Request
                    </button>
                  )}
                </>
              ) : (
                <form onSubmit={(e) => { e.preventDefault(); handleCreateRequest(); }}>
                  {/* Show remaining days info when creating request */}
                  {vacationBalance && (
                    <div className="request-info">
                      <span>Remaining days: {vacationBalance.remaining_days}</span>
                    </div>
                  )}
                  
                  <div className="form-group">
                    <label>Start Date</label>
                    <input
                      type="date"
                      value={newRequest.start_date}
                      onChange={(e) => setNewRequest({ ...newRequest, start_date: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>End Date</label>
                    <input
                      type="date"
                      value={newRequest.end_date}
                      onChange={(e) => setNewRequest({ ...newRequest, end_date: e.target.value })}
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label>Type</label>
                    <select
                      value={newRequest.vacation_type}
                      onChange={(e) => setNewRequest({ ...newRequest, vacation_type: e.target.value })}
                    >
                      <option value="annual">Annual Leave</option>
                      <option value="sick">Sick Leave</option>
                      <option value="personal">Personal</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Reason (optional)</label>
                    <textarea
                      value={newRequest.reason}
                      onChange={(e) => setNewRequest({ ...newRequest, reason: e.target.value })}
                      rows={3}
                    />
                  </div>
                  <button type="submit" className="btn btn-primary">Submit Request</button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
      
      {/* Approve/Reject Modal */}
      {showActionModal && (
        <div className="modal-overlay" onClick={() => setShowActionModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{actionType === 'approve' ? 'Approve' : 'Reject'} Request</h3>
              <button className="modal-close" onClick={() => setShowActionModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Comment (optional)</label>
                <textarea
                  value={actionComment}
                  onChange={(e) => setActionComment(e.target.value)}
                  rows={3}
                  placeholder="Add a comment for the employee..."
                />
              </div>
              <div className="modal-actions">
                <button 
                  className={`btn ${actionType === 'approve' ? 'btn-success' : 'btn-danger'}`}
                  onClick={() => handleApproveReject(actionType)}
                >
                  {actionType === 'approve' ? 'Approve' : 'Reject'}
                </button>
                <button className="btn btn-secondary" onClick={() => setShowActionModal(false)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
