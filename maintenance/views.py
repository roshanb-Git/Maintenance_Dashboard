
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Equipment,
    MaintenanceSchedule,
    Site,
)


@login_required
def dashboard(request):

    today = timezone.localdate()

    warning_date = today + timedelta(days=15)

    schedules = MaintenanceSchedule.objects.filter(
        equipment__active=True
    ).select_related(
        "equipment",
        "equipment__site"
    )

    site_id = request.GET.get("site")

    if site_id:
        schedules = schedules.filter(
            equipment__site_id=site_id
        )

    total_equipment = Equipment.objects.filter(
        active=True
    )

    if site_id:
        total_equipment = total_equipment.filter(
            site_id=site_id
        )

    context = {
        "total_equipment": total_equipment.count(),

        "overdue": schedules.filter(
            next_due__lt=today
        ).count(),

        "due_today": schedules.filter(
            next_due=today
        ).count(),

        "due_soon": schedules.filter(
            next_due__gt=today,
            next_due__lte=warning_date
        ).count(),

        "on_track": schedules.filter(
            next_due__gt=warning_date
        ).count(),

        "schedules": schedules.order_by("next_due"),

        "sites": Site.objects.all(),

        "selected_site": site_id,
    }

    return render(
        request,
        "maintenance/dashboard.html",
        context
    )
