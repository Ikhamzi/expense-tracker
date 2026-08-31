"""Small, framework-free business rules that don't belong to any one
database table or API endpoint.

Most validation in this app is simple field validation (is this a valid
email, is the password long enough) and Pydantic already handles that in
interfaces/api/schemas.py. The one rule that's genuinely a *business* rule
rather than a field-shape rule is "a month filter must be a real YYYY-MM
month" - it's used by both the expense list endpoint and the summary
endpoint, it has actual logic (turning "2026-02" into a first/last day and
rejecting nonsense like month 13), and it shouldn't know anything about
FastAPI or HTTP. That's why it lives here instead of in the application or
interface layers.
"""

from calendar import monthrange
from datetime import date

from domain.errors import ValidationError


def parse_month_range(month: str) -> tuple[date, date]:
    """Turn 'YYYY-MM' into (first day of month, last day of month).

    Raises domain.errors.ValidationError if `month` isn't a real YYYY-MM
    string - the interface layer turns that into the same HTTP 400 response
    this API has always returned for a bad month filter.
    """
    try:
        year_str, month_str = month.split("-")
        year, mon = int(year_str), int(month_str)
        first_day = date(year, mon, 1)
        last_day = date(year, mon, monthrange(year, mon)[1])
    except (ValueError, IndexError):
        raise ValidationError("month must be in YYYY-MM format")
    return first_day, last_day
