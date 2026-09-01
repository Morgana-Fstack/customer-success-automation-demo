"""Customer relationship tracking model for daily CS follow-up workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class ContactStatus(StrEnum):
    """Operational status of the latest customer contact."""

    NOT_CONTACTED = "Not contacted"
    CONTACTED = "Contacted"
    FOLLOW_UP_DUE = "Follow-up due"
    WAITING = "Waiting"


class ResponseStatus(StrEnum):
    """Customer response state after a contact attempt."""

    NOT_APPLICABLE = "Not applicable"
    RESPONDED = "Responded"
    NO_RESPONSE = "No response"
    WAITING = "Waiting"
    GHOSTED = "Ghosted"


class NextAction(StrEnum):
    """Standard next actions used by the CS daily queue."""

    CONTACT_TODAY = "Contact today"
    FOLLOW_UP_TODAY = "Follow up today"
    FOLLOW_UP_TOMORROW = "Follow up tomorrow"
    WAIT_FOR_RESPONSE = "Wait for response"
    REACTIVATE_CUSTOMER = "Reactivate customer"
    SCHEDULE_RENEWAL = "Schedule renewal conversation"
    NO_ACTION = "No action"


@dataclass(frozen=True)
class CustomerTracking:
    """Relationship state used to decide what a CSM should do next."""

    customer_id: str
    customer_name: str
    owner: str | None = None
    last_contact_date: date | None = None
    next_contact_date: date | None = None
    contact_status: ContactStatus = ContactStatus.NOT_CONTACTED
    response_status: ResponseStatus = ResponseStatus.NOT_APPLICABLE
    follow_up_count: int = 0
    renewal_days: int | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if self.follow_up_count < 0:
            raise ValueError("follow_up_count cannot be negative")
        if self.renewal_days is not None and self.renewal_days < 0:
            raise ValueError("renewal_days cannot be negative")
