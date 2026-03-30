from decimal import Decimal

from app.services.alert_rules import next_below_state, should_create_alert


def test_should_create_alert_only_on_crossing() -> None:
    assert (
        should_create_alert(
            was_below_desired=False,
            current_price=Decimal("99.00"),
            desired_price=Decimal("100.00"),
            in_stock=True,
        )
        is True
    )
    assert (
        should_create_alert(
            was_below_desired=True,
            current_price=Decimal("95.00"),
            desired_price=Decimal("100.00"),
            in_stock=True,
        )
        is False
    )


def test_next_below_state_resets_if_unavailable() -> None:
    assert (
        next_below_state(
            current_price=None,
            desired_price=Decimal("100.00"),
            in_stock=False,
        )
        is False
    )
