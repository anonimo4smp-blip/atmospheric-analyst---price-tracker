from decimal import Decimal


def should_create_alert(
    was_below_desired: bool,
    current_price: Decimal | None,
    desired_price: Decimal,
    in_stock: bool,
) -> bool:
    if not in_stock or current_price is None:
        return False
    is_below = current_price <= desired_price
    return is_below and not was_below_desired


def next_below_state(
    current_price: Decimal | None,
    desired_price: Decimal,
    in_stock: bool,
) -> bool:
    if not in_stock or current_price is None:
        return False
    return current_price <= desired_price
