import re
from decimal import Decimal, InvalidOperation


def parse_price_to_decimal(raw_price: str) -> Decimal:
    cleaned = raw_price.replace("\xa0", " ").strip()
    cleaned = re.sub(r"[^\d,.\-]", "", cleaned)

    if not cleaned:
        raise ValueError("No se encontró un valor de precio válido.")

    # Maneja formato europeo: 1.234,56
    if "," in cleaned and "." in cleaned and cleaned.rfind(",") > cleaned.rfind("."):
        cleaned = cleaned.replace(".", "")
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    else:
        cleaned = cleaned.replace(",", "")

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"No se pudo convertir el precio: {raw_price}") from exc

    if value <= 0:
        raise ValueError(f"Precio inválido detectado: {raw_price}")

    return value.quantize(Decimal("0.01"))
