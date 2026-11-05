
from django.contrib import admin

from .models import (
    Site,
    Equipment,
    MaintenanceSchedule,
    MaintenanceHistory,
    MaintenanceAttachment,
    DieselFilling,
)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location")
    search_fields = ("code", "name")
    ordering = ("code",)   # A to Z by Equipment ID


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "equipment_id",
        "name",
        "equipment_type",
        "site",
        "active",
    )

    list_filter = ("site", "equipment_type", "active")
    search_fields = ("equipment_id", "Make")
    ordering = ("equipment_id",)   # A to Z by Equipment ID


@admin.register(MaintenanceSchedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = (
        "equipment",
        "task_type",
        "interval_months",
        "last_completed",
        "next_due",
        "status",
    )

    list_filter = ("task_type", "equipment__site")


admin.site.register(MaintenanceHistory)
admin.site.register(MaintenanceAttachment)

@admin.register(DieselFilling)
class DieselFillingAdmin(admin.ModelAdmin):
    list_display = ("equipment", "filled_date", "litres", "running_hours", "recorded_by")
    list_filter = ("equipment__site", "filled_date")
