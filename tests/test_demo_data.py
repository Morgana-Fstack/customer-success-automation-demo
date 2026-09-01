from datetime import date

from src.demo_data import build_demo_customers


def test_demo_portfolio_contains_operational_and_historical_scenarios() -> None:
    customers = build_demo_customers(date(2026, 9, 1))

    assert len(customers) == 6
    assert set(customers["customer_status"]) == {"Active", "Cancelled", "Desistencia"}
    assert set(customers.loc[customers["customer_status"] == "Active", "platform_status"]) == {
        "Healthy",
        "AtRisk",
        "Dormant",
        "NeverActivated",
    }
    assert customers["customer_id"].is_unique


def test_demo_dates_move_with_presentation_day() -> None:
    today = date(2026, 9, 1)
    customers = build_demo_customers(today)
    aurora = customers.loc[customers["customer_id"] == "DEMO-001"].iloc[0]

    assert aurora["next_contact_date"] == today
    assert aurora["last_platform_activity_date"] == date(2026, 8, 31)
