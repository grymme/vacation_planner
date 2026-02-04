import React, { useEffect, useState } from 'react';
import { vacationBalanceApi, VacationBalance } from '../api/vacation';
import './VacationBalance.css';

export const VacationBalance: React.FC = () => {
  const [balance, setBalance] = useState<VacationBalance | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchBalance = async () => {
      try {
        const data = await vacationBalanceApi.getVacationBalance();
        setBalance(data);
      } catch (err) {
        console.error('Failed to fetch vacation balance:', err);
        setError('Failed to load balance');
      } finally {
        setIsLoading(false);
      }
    };

    fetchBalance();
  }, []);

  if (isLoading) return <div className="vacation-balance loading">Loading...</div>;
  if (error) return <div className="vacation-balance error">{error}</div>;
  if (!balance) return <div className="vacation-balance empty">No vacation period active</div>;

  return (
    <div className="vacation-balance">
      <h3>Vacation Balance ({balance.vacation_period.name})</h3>
      <div className="balance-cards">
        <div className="balance-card total">
          <span className="label">Total Available</span>
          <span className="value">{balance.total_available} days</span>
        </div>
        <div className="balance-card approved">
          <span className="label">Approved</span>
          <span className="value">{balance.approved_days} days</span>
        </div>
        <div className="balance-card pending">
          <span className="label">Pending</span>
          <span className="value">{balance.pending_days} days</span>
        </div>
        <div className="balance-card remaining">
          <span className="label">Remaining</span>
          <span className="value">{balance.remaining_days} days</span>
        </div>
      </div>
      <div className="period-dates">
        {balance.vacation_period.start_date} - {balance.vacation_period.end_date}
      </div>
    </div>
  );
};
