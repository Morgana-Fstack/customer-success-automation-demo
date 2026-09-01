from datetime import date

from src.config import ContactPriorityConfig
from src.contact_priority import evaluate_contact_priority
from src.tracking import CustomerTracking, ResponseStatus

TODAY = date(2026, 8, 26)


def test_low_contact_priority_when_nothing_is_due() -> None:
    tracking = CustomerTracking(
        customer_id="C-001",
        customer_name="Low Priority",
        last_contact_date=date(2026, 8, 25),
        next_contact_date=date(2026, 8, 30),
        response_status=ResponseStatus.RESPONDED,
        follow_up_count=0,
        renewal_days=90,
    )

    result = evaluate_contact_priority(tracking, today=TODAY)

    assert result["contact_priority_score"] == 0
    assert result["contact_priority"] == "Low"


def test_high_contact_priority_for_overdue_silent_renewal_customer() -> None:
    tracking = CustomerTracking(
        customer_id="C-002",
        customer_name="High Priority",
        last_contact_date=date(2026, 8, 20),
        next_contact_date=date(2026, 8, 25),
        response_status=ResponseStatus.NO_RESPONSE,
        follow_up_count=2,
        renewal_days=15,
    )

    result = evaluate_contact_priority(tracking, today=TODAY)

    assert result["contact_priority_score"] == 90
    assert result["contact_priority"] == "High"
    assert result["next_contact_action"] == "Schedule renewal conversation"


def test_contact_priority_uses_custom_configuration() -> None:
    tracking = CustomerTracking(
        customer_id="C-003",
        customer_name="Custom Rules",
        next_contact_date=TODAY,
        response_status=ResponseStatus.NO_RESPONSE,
        follow_up_count=1,
        renewal_days=20,
    )
    config = ContactPriorityConfig(
        overdue_contact_weight=10,
        no_response_weight=10,
        ghosted_weight=10,
        repeated_follow_up_weight=10,
        renewal_weight=10,
        follow_up_threshold=1,
        renewal_window_days=30,
        high_priority_threshold=80,
        medium_priority_threshold=30,
    )

    result = evaluate_contact_priority(tracking, today=TODAY, config=config)

    assert result["contact_priority_score"] == 40
    assert result["contact_priority"] == "Medium"
