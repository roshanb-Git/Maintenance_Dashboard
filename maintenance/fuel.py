from decimal import Decimal

from .models import DailyReading


def estimate_fuel(gen, filling):
    """
    Estimate a generator's current tank level.
    Baseline: tank_level_after of the latest filling.
    Hours used: latest daily reading minus the meter at the time of filling.
    """
    out = {"level": None, "hours_used": None, "reading_date": None, "estimated": False}

    if not filling or filling.tank_level_after is None:
        return out

    level = filling.tank_level_after
    out["level"] = level                     
    
    # fallback: level at last filling
    if not gen.consumption_lph:
        return out

    readings = DailyReading.objects.filter(equipment=gen)
    latest = readings.filter(reading_date__gte=filling.filled_date).first()
    if not latest:
        return out

    # Meter at filling time: the filling's own running_hours if entered,
    # otherwise the closest daily reading on/before the fill date,
    # otherwise the first reading after it.
    start = filling.running_hours
    if start is None:
        base = (
            readings.filter(reading_date__lte=filling.filled_date).first()
            or readings.filter(reading_date__gte=filling.filled_date)
                       .order_by("reading_date").first()
        )
        start = base.running_hours if base else None
    if start is None:
        return out

    hours = max(Decimal("0"), latest.running_hours - start)
    out.update(
        level=max(Decimal("0"), level - hours * gen.consumption_lph),
        hours_used=hours,
        reading_date=latest.reading_date,
        estimated=True,
    )
    return out