
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import MaintenanceUpdateForm
from .models import Equipment, MaintenanceAttachment, MaintenanceSchedule
from .services import allowed_sites
from django.http import FileResponse, Http404


@login_required
def dashboard(request):

    today = timezone.localdate()
    warning_date = today + timedelta(days=15)
    sites = allowed_sites(request.user)


    schedules = MaintenanceSchedule.objects.filter(
        equipment__active=True,
        equipment__site__in=sites,
    ).select_related(
        "equipment",
        "equipment__site"
    )


    site_id = request.GET.get("site" , "")

    total_equipment = Equipment.objects.filter(
        active=True,
        site__in=sites,
    )

    if site_id.isdigit():
        schedules = schedules.filter(equipment__site_id=site_id)
        total_equipment = total_equipment.filter(site_id=site_id)


    context = {
        "total_equipment": total_equipment.count(),

        "overdue": schedules.filter(
            next_due__lt=today
        ).count(),

        "due_today": schedules.filter(
            next_due=today
        ).count(),

        "due_soon": schedules.filter(
            next_due__gte=today,
            next_due__lte=warning_date
        ).count(),

        "on_track": schedules.filter(
            next_due__gt=warning_date
        ).count(),

        "schedules": schedules.order_by("next_due"),

        "todo": schedules.filter(
            next_due__lte=warning_date
        ).order_by("next_due"),

        "sites": sites,

        "selected_site": site_id,
    }

    return render(
        request,
        "maintenance/dashboard.html",
        context
    )



#This function powers the Update page.

@login_required
@permission_required("maintenance.add_maintenancehistory", raise_exception=True)
def complete_maintenance(request, schedule_id):
    schedule = get_object_or_404(
        MaintenanceSchedule,
        id=schedule_id,
        equipment__site__in=allowed_sites(request.user),
    )
    form = MaintenanceUpdateForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            history = form.save(commit=False)
            history.schedule = schedule
            history.technician = request.user
            history.save()

            f = form.cleaned_data.get("attachment")
            if f:
                MaintenanceAttachment.objects.create(history=history, file=f)

            # Only move the schedule forward, never backwards
            if history.completed_date > schedule.last_completed:
                schedule.last_completed = history.completed_date
                schedule.save()


        messages.success(request, "Maintenance record saved.")
        return redirect("dashboard")

    return render(
        request,
        "maintenance/maintenance_form.html",
        {"form": form, "schedule": schedule},
    )


@login_required
def equipment_list(request):
    items = Equipment.objects.filter(
        site__in=allowed_sites(request.user)
    ).select_related("site")
    return render(request, "maintenance/equipment.html", {"equipment": items})


@login_required
def reports(request):
    return render(request, "maintenance/reports.html")


@login_required
def todo(request):
    today = timezone.localdate()
    warning_date = today + timedelta(days=15)
    items = MaintenanceSchedule.objects.filter(
        equipment__active=True,
        equipment__site__in=allowed_sites(request.user),
        next_due__lte=warning_date,
    ).select_related("equipment", "equipment__site").order_by("next_due")
    return render(request, "maintenance/todo.html", {"todo": items})