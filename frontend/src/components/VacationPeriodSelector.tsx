import React, { useEffect, useState } from 'react';
import { vacationPeriodsApi, VacationPeriod } from '../api/vacation';
import './VacationPeriodSelector.css';

interface VacationPeriodSelectorProps {
  selectedPeriodId: string | null;
  onChange: (periodId: string) => void;
}

export const VacationPeriodSelector: React.FC<VacationPeriodSelectorProps> = ({
  selectedPeriodId,
  onChange
}) => {
  const [periods, setPeriods] = useState<VacationPeriod[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchPeriods = async () => {
      try {
        const data = await vacationPeriodsApi.getVacationPeriods();
        setPeriods(data);
        // Auto-select default period if none selected
        if (!selectedPeriodId && data.length > 0) {
          const defaultPeriod = data.find(p => p.is_default);
          if (defaultPeriod) {
            onChange(defaultPeriod.id);
          }
        }
      } catch (err) {
        console.error('Failed to fetch vacation periods:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPeriods();
  }, [onChange, selectedPeriodId]);

  if (isLoading) return <div className="vacation-period-selector loading">Loading periods...</div>;
  if (!periods.length) return null;

  return (
    <div className="vacation-period-selector">
      <label htmlFor="period-select">Vacation Period:</label>
      <select
        id="period-select"
        value={selectedPeriodId || ''}
        onChange={(e) => onChange(e.target.value)}
      >
        {periods.map((period) => (
          <option key={period.id} value={period.id}>
            {period.name} {period.is_default && '(Default)'}
          </option>
        ))}
      </select>
    </div>
  );
};
