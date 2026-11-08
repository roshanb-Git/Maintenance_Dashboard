
from datetime import timedelta, date
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone


from .forms import MaintenanceUpdateForm , DieselFillingForm
from .models import Equipment, MaintenanceAttachment, MaintenanceSchedule, DieselFilling
from .services import allowed_sites
from django.http import FileResponse, Http404
from django.db.models import OuterRef, Q, Subquery, Sum
from django.utils.dateparse import parse_date


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
            history.due_date = schedule.next_due
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

    return render(request,"maintenance/maintenance_form.html",
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


@login_required
def history(request):
    qs = (maintenancehistory.objects
        # Only records for sites this user is allowed to see
        .filter(schedule__equipment__site__in=allowed_sites(request.user))
        .select_related("schedule__equipment__site", "technician")
        .prefetch_related("attachments")     # avoids one query per row for Files
        .order_by("-completed_date", "-id")  # newest first
    )
 
    # Filter values from the form: ?site=&task=&equipment=&from=&to=
    site = request.GET.get("site", "")
    task = request.GET.get("task", "")
    equipment = request.GET.get("equipment", "").strip()
    date_from = parse_date(request.GET.get("from", "") or "")
    date_to = parse_date(request.GET.get("to", "") or "")
 
    if site.isdigit():
        qs = qs.filter(schedule__equipment__site_id=site)
    if task:
        qs = qs.filter(schedule__task_type=task)
    if equipment:
        qs = qs.filter(schedule__equipment__equipment_id__icontains=equipment)
    if date_from:
        qs = qs.filter(completed_date__gte=date_from)
    if date_to:
        qs = qs.filter(completed_date__lte=date_to)
 
    return render(request, "maintenance/history.html", {
        "records": qs,
        "sites": allowed_sites(request.user),
        "tasks": MaintenanceSchedule.TASKS,
        # Sent back so the filter form keeps the values the user typed
        "selected": {
            "site": site,
            "task": task,
            "equipment": equipment,
            "from": request.GET.get("from", ""),
            "to": request.GET.get("to", ""),
        },
    })



# Reports page (static for now)
@login_required
def reports(request):
    return render(request, "maintenance/reports.html")


@login_required
def diesel(request):
    sites = allowed_sites(request.user)
    selected_site = request.GET.get("site", "")
    today = timezone.localdate()
    since = today - timedelta(days=30)

    # Latest filling per generator (newest date first, then newest id)
    last = DieselFilling.objects.filter(
        equipment=OuterRef("pk")
    ).order_by("-filled_date", "-id")

    qs = Equipment.objects.filter(
        equipment_type="DEG", active=True, site__in=sites
    ).select_related("site")

    if selected_site.isdigit():
        qs = qs.filter(site_id=selected_site)

     # Attach latest-filling details and 30-day litres to each generator
    qs = qs.annotate(
        last_fill_id=Subquery(last.values("id")[:1]),          
        #NEW: sort tie-breaker
        last_fill_date=Subquery(last.values("filled_date")[:1]),
        last_fill_litres=Subquery(last.values("litres")[:1]),
        last_level=Subquery(last.values("tank_level_after")[:1]),
        litres_30=Sum("diesel_fills__litres",
                      filter=Q(diesel_fills__filled_date__gte=since)),
    )

    generators = []
    site_totals = {}
    stats = {"total": 0, "critical": 0, "low": 0, "unknown": 0, "litres_30": 0}

    for g in qs:
        cap = g.tank_capacity_litres
        if cap and g.last_level is not None:
            g.pct = max(0, min(100, round(float(g.last_level) / float(cap) * 100)))
            # thresholds: change 25 and 50 if you want different limits
            g.level_status = ("critical" if g.pct < 25
                              else "low" if g.pct < 50 else "ok")
        else:
            g.pct = None
            g.level_status = "unknown"

        g.litres_30 = g.litres_30 or 0
        g.days_since = (today - g.last_fill_date).days if g.last_fill_date else None

        # Summary card totals
        stats["total"] += 1
        stats["litres_30"] += g.litres_30
        if g.level_status in stats:
            stats[g.level_status] += 1

         # Per-site totals
        s = site_totals.setdefault(
            g.site_id, {"name": g.site.name, "count": 0, "litres_30": 0})
        s["count"] += 1
        s["litres_30"] += g.litres_30

        generators.append(g)

    # lowest fuel first, generators with no data last
    generators.sort(key=lambda x: (x.pct is None, x.pct or 0, x.site.name))

    site_list = sorted(site_totals.values(), key=lambda x: -x["litres_30"])
    top = site_list[0]["litres_30"] if site_list else 0
    for s in site_list:
        s["bar"] = round(s["litres_30"] / top * 100) if top else 0

    return render(request, "maintenance/diesel_overview.html", {
        "generators": generators,
        "site_list": site_list,
        "stats": stats,
        "sites": sites,
        "selected_site": selected_site,
    })




# Add-diesel page: form to record a new diesel filling for one generator (this was the missing view).
@login_required
@permission_required("maintenance.add_dieselfilling", raise_exception=True)
def add_diesel(request, equipment_id):
    equipment = get_object_or_404(
        Equipment,
        id=equipment_id,
        equipment_type="DEG",
        active=True,
        site__in=allowed_sites(request.user),
    )
    form = DieselFillingForm(request.POST or None, equipment=equipment)

    if request.method == "POST" and form.is_valid():
        filling = form.save(commit=False)
        filling.equipment = equipment
        filling.recorded_by = request.user   # delete this line if your model has no filled_by field
        filling.save()
        messages.success(request, f"Diesel filling saved for {equipment}.")
        return redirect("diesel")

    return render(
        request,
        "maintenance/diesel_form.html",
        {"form": form, "equipment": equipment},
    )