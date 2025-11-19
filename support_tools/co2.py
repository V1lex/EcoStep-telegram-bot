"""
Helpers for working with CO₂ values stored as free-form strings.
"""

from __future__ import annotations

import re

CO2_PATTERN = re.compile(r"[-+]?\d+[.,]?\d*")


def parse_co2_value(raw_value: str | None) -> float | None:
    """
    Extract numeric CO₂ amount from a value like "1.2 кг CO₂".

    Returns None if parsing fails.
    """
    if not raw_value:
        return None
    match = CO2_PATTERN.search(str(raw_value))
    if not match:
        return None
    normalized = match.group(0).replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None
