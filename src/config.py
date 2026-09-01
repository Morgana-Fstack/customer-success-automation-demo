"""Configuration objects for Customer Success automation rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    """Configurable thresholds and weights for customer risk detection."""

    stale_contact_days: int = 30
    renewal_window_days: int = 60
    open_tickets_threshold: int = 2
    stale_contact_weight: int = 40
    renewal_weight: int = 35
    open_tickets_weight: int = 25
    high_risk_threshold: int = 70
    medium_risk_threshold: int = 35


@dataclass(frozen=True)
class ContactPriorityConfig:
    """Configurable thresholds and weights for daily contact prioritization."""

    overdue_contact_weight: int = 35
    no_response_weight: int = 20
    ghosted_weight: int = 35
    repeated_follow_up_weight: int = 15
    renewal_weight: int = 20
    follow_up_threshold: int = 2
    renewal_window_days: int = 30
    high_priority_threshold: int = 60
    medium_priority_threshold: int = 30


DEFAULT_RISK_CONFIG = RiskConfig()
DEFAULT_CONTACT_PRIORITY_CONFIG = ContactPriorityConfig()
