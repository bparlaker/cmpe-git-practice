"""
Unit helpers (FR-3.3).

People can enter 1.2 m or 120 cm. I always save the value in a base unit:
centimeters for length and grams for weight. Then searching and filtering
work the same for every entry, whatever unit the user typed.
"""

# How many base units are in one of each unit.
LENGTH_UNITS = {"mm": 0.1, "cm": 1, "m": 100}
WEIGHT_UNITS = {"g": 1, "kg": 1000}

UNIT_CHOICES = [
    ("mm", "mm"),
    ("cm", "cm"),
    ("m", "m"),
    ("g", "g"),
    ("kg", "kg"),
]


def units_like(unit):
    """All units of the same kind. For "cm" I get ["mm", "cm", "m"]."""
    if unit in LENGTH_UNITS:
        return list(LENGTH_UNITS)
    if unit in WEIGHT_UNITS:
        return list(WEIGHT_UNITS)
    return [unit] if unit else []


def factor(unit):
    if unit in LENGTH_UNITS:
        return LENGTH_UNITS[unit]
    if unit in WEIGHT_UNITS:
        return WEIGHT_UNITS[unit]
    # Unknown unit: I do not convert anything.
    return 1


def to_base(value, unit):
    """120 cm -> 120, 1.2 m -> 120, 2 kg -> 2000"""
    if value is None:
        return None
    return value * factor(unit)


def from_base(value, unit):
    """The other way: 120 (cm) shown in m -> 1.2"""
    if value is None:
        return None
    return round(value / factor(unit), 3)
