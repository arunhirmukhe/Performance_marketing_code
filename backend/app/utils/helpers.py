"""General helper utilities."""

from datetime import datetime, date, timedelta
from typing import Optional


def get_date_range(days_back: int = 7) -> tuple[date, date]:
    """Get a date range from today going back N days."""
    end_date = date.today() - timedelta(days=1)  # Yesterday
    start_date = end_date - timedelta(days=days_back - 1)
    return start_date, end_date


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default on division by zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_roas(revenue: float, spend: float) -> float:
    """Calculate Return on Ad Spend."""
    return safe_divide(revenue, spend)


def calculate_cpa(spend: float, conversions: int) -> float:
    """Calculate Cost Per Acquisition."""
    return safe_divide(spend, conversions)


def calculate_ctr(clicks: int, impressions: int) -> float:
    """Calculate Click-Through Rate."""
    return safe_divide(clicks, impressions)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format a monetary amount."""
    return f"${amount:,.2f}" if currency == "USD" else f"{amount:,.2f} {currency}"


def percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    return safe_divide(new_value - old_value, abs(old_value)) * 100
