"""Unit tests for utility functions in the Vacation Planner application."""
import pytest
from datetime import date
from uuid import uuid4

from app.utils import calculate_business_days, get_vacation_period_for_date
from app.models import VacationPeriod


# =============================================================================
# calculate_business_days Tests
# =============================================================================
class TestCalculateBusinessDays:
    """Tests for the calculate_business_days function."""

    def test_calculate_business_days_simple(self):
        """Test basic weekday calculation (Mon-Fri)."""
        # Apr 1, 2024 (Mon) to Apr 5, 2024 (Fri) = 5 weekdays
        assert calculate_business_days(date(2024, 4, 1), date(2024, 4, 5)) == 5

    def test_calculate_business_days_with_weekend(self):
        """Test that weekends are excluded."""
        # Apr 1 (Mon) to Apr 7 (Sun) = 5 weekdays (Mon-Fri)
        assert calculate_business_days(date(2024, 4, 1), date(2024, 4, 7)) == 5

    def test_calculate_business_days_only_weekend(self):
        """Test weekend-only period returns 0."""
        # Apr 6 (Sat) to Apr 7 (Sun) = 0 weekdays
        assert calculate_business_days(date(2024, 4, 6), date(2024, 4, 7)) == 0

    def test_calculate_business_days_single_day(self):
        """Test single day calculation."""
        assert calculate_business_days(date(2024, 4, 1), date(2024, 4, 1)) == 1

    def test_calculate_business_days_start_after_end(self):
        """Test when start date is after end date returns 0."""
        assert calculate_business_days(date(2024, 4, 5), date(2024, 4, 1)) == 0

    def test_calculate_business_days_full_week(self):
        """Test full week returns 5 business days."""
        # Apr 1 (Mon) to Apr 14 (Sun) = 10 business days (2 weeks)
        assert calculate_business_days(date(2024, 4, 1), date(2024, 4, 14)) == 10

    def test_calculate_business_days_month_spanning(self):
        """Test calculation spanning months."""
        # Apr 29 (Mon) to May 3 (Fri) = 5 business days
        assert calculate_business_days(date(2024, 4, 29), date(2024, 5, 3)) == 5

    def test_calculate_business_days_year_spanning(self):
        """Test calculation spanning years."""
        # Dec 30, 2024 (Mon) to Jan 3, 2025 (Fri) = 5 business days
        assert calculate_business_days(date(2024, 12, 30), date(2025, 1, 3)) == 5

    def test_calculate_business_days_all_saturdays(self):
        """Test Saturdays only returns 0."""
        # Apr 6 is Saturday, Apr 8 is Monday - checking single Saturday
        assert calculate_business_days(date(2024, 4, 6), date(2024, 4, 6)) == 0

    def test_calculate_business_days_all_sundays(self):
        """Test Sundays only returns 0."""
        # Apr 7 is Sunday, Apr 8 is Monday - checking single Sunday
        assert calculate_business_days(date(2024, 4, 7), date(2024, 4, 7)) == 0


# =============================================================================
# get_vacation_period_for_date Tests
# =============================================================================
class TestGetVacationPeriodForDate:
    """Tests for the get_vacation_period_for_date function."""

    def test_get_vacation_period_for_date_found(self):
        """Test finding period that contains the date."""
        period = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_default=True
        )
        result = get_vacation_period_for_date(date(2024, 6, 15), [period])
        assert result == period

    def test_get_vacation_period_for_date_not_found(self):
        """Test when date is outside all periods."""
        period = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 4, 1),
            end_date=date(2024, 6, 30),
            is_default=False
        )
        result = get_vacation_period_for_date(date(2024, 8, 1), [period])
        assert result is None

    def test_get_vacation_period_for_date_on_start_date(self):
        """Test finding period when date is exactly on start date."""
        period = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_default=True
        )
        result = get_vacation_period_for_date(date(2024, 4, 1), [period])
        assert result == period

    def test_get_vacation_period_for_date_on_end_date(self):
        """Test finding period when date is exactly on end date."""
        period = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_default=True
        )
        result = get_vacation_period_for_date(date(2025, 3, 31), [period])
        assert result == period

    def test_get_vacation_period_for_date_empty_list(self):
        """Test with empty list returns None."""
        result = get_vacation_period_for_date(date(2024, 6, 15), [])
        assert result is None

    def test_get_vacation_period_for_date_multiple_periods(self):
        """Test finding period when multiple periods exist."""
        period1 = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2023-2024",
            start_date=date(2023, 4, 1),
            end_date=date(2024, 3, 31),
            is_default=False
        )
        period2 = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_default=True
        )
        periods = [period1, period2]
        
        # Date in first period
        result1 = get_vacation_period_for_date(date(2024, 1, 15), periods)
        assert result1 == period1
        
        # Date in second period
        result2 = get_vacation_period_for_date(date(2024, 6, 15), periods)
        assert result2 == period2

    def test_get_vacation_period_for_date_returns_first_match(self):
        """Test that first matching period is returned."""
        period1 = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            is_default=False
        )
        period2 = VacationPeriod(
            id=uuid4(),
            company_id=uuid4(),
            name="2024-2025-extended",
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
            is_default=True
        )
        periods = [period1, period2]
        
        # Should return first match (period1) since it comes first in the list
        result = get_vacation_period_for_date(date(2024, 6, 15), periods)
        assert result == period1
