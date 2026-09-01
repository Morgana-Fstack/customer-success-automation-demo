"""Daily contact-priority scoring for Customer Success follow-up queues."""

from __future__ import annotations

from datetime import date, timedelta

from src.config import ContactPriorityConfig, DEFAULT_CONTACT_PRIORITY_CONFIG
from src.tracking import CustomerTracking, NextAction, ResponseStatus


def calculate_contact_priority_score(
    tracking: CustomerTracking,
    *,
    today: date | None = None,
    config: ContactPriorityConfig = DEFAULT_CONTACT_PRIORITY_CONFIG,
) -> int:
    """Return a transparent 0-100 priority score for the next customer contact."""
    reference_date = today or date.today()
    score = 0

    if tracking.next_contact_date is not None and tracking.next_contact_date <= reference_date:
        score += config.overdue_contact_weight

    if tracking.response_status == ResponseStatus.NO_RESPONSE:
        score += config.no_response_weight
    elif tracking.response_status == ResponseStatus.GHOSTED:
        score += config.ghosted_weight

    if tracking.follow_up_count >= config.follow_up_threshold:
        score += config.repeated_follow_up_weight

    if tracking.renewal_days is not None and tracking.renewal_days <= config.renewal_window_days:
        score += config.renewal_weight

    return min(score, 100)


def classify_contact_priority(
    score: int,
    config: ContactPriorityConfig = DEFAULT_CONTACT_PRIORITY_CONFIG,
) -> str:
    """Classify a contact-priority score as Low, Medium or High."""
    if score >= config.high_priority_threshold:
        return "High"
    if score >= config.medium_priority_threshold:
        return "Medium"
    return "Low"


def recommend_contact_action(
    tracking: CustomerTracking,
    *,
    today: date | None = None,
) -> NextAction:
    """Recommend the next operational action for a customer relationship."""
    reference_date = today or date.today()

    if tracking.response_status == ResponseStatus.GHOSTED:
        return NextAction.REACTIVATE_CUSTOMER

    if tracking.renewal_days is not None and tracking.renewal_days <= 30:
        return NextAction.SCHEDULE_RENEWAL

    if tracking.next_contact_date is not None and tracking.next_contact_date <= reference_date:
        return NextAction.FOLLOW_UP_TODAY

    if tracking.response_status == ResponseStatus.NO_RESPONSE:
        return NextAction.FOLLOW_UP_TOMORROW

    if tracking.response_status == ResponseStatus.WAITING:
        return NextAction.WAIT_FOR_RESPONSE

    if tracking.last_contact_date is None:
        return NextAction.CONTACT_TODAY

    if tracking.next_contact_date == reference_date + timedelta(days=1):
        return NextAction.FOLLOW_UP_TOMORROW

    return NextAction.NO_ACTION


def evaluate_contact_priority(
    tracking: CustomerTracking,
    *,
    today: date | None = None,
    config: ContactPriorityConfig = DEFAULT_CONTACT_PRIORITY_CONFIG,
) -> dict[str, int | str]:
    """Return score, priority level and recommended next action."""
    score = calculate_contact_priority_score(tracking, today=today, config=config)
    return {
        "contact_priority_score": score,
        "contact_priority": classify_contact_priority(score, config),
        "next_contact_action": recommend_contact_action(tracking, today=today).value,
    }
