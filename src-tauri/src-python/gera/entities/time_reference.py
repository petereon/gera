"""Time reference model for task entity inline references.

Captures the full parsed structure of ``@before[2d]:event-id`` and
``@after[1h]:event-id`` so the service layer can resolve against the DB.
"""

from __future__ import annotations

from pydantic import BaseModel


class TimeReference(BaseModel):
    """A parsed time-offset reference from a task line.

    Examples::

        @before[2d]:standup-feb-20  → modifier="before", amount=2, unit="d", target_id="standup-feb-20"
        @after[1h]:review-mar-01    → modifier="after",  amount=1, unit="h", target_id="review-mar-01"
    """

    modifier: str
    """``"before"`` or ``"after"``."""

    amount: int
    """Numeric offset value."""

    unit: str
    """One of ``Y``, ``M``, ``W``, ``d``, ``h``, ``m``."""

    target_id: str
    """The referenced event ID."""
