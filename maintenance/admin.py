
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
    list_display = ("equipment_id","name","equipment_type","site","active",)
    list_filter = ("site", "equipment_type", "active")

    BASE_FIELDS = ["equipment_id", "name", "equipment_type", "site", "make", "active"]
    search_fields = ("equipment_id", "Make")
    ordering = ("equipment_id",)   # A to Z by Equipment ID
    def get_fields(self, request, obj=None):
        # 1) type chosen on a submitted form, 2) saved record, 3) ?equipment_type=DEG in the URL
        eq_type = (
            request.POST.get("equipment_type")
            or (obj.equipment_type if obj else request.GET.get("equipment_type"))
        )

        if eq_type == "DEG":
            return self.BASE_FIELDS + list(Equipment.DEG_ONLY_FIELDS)  # generators: show them
        return self.BASE_FIELDS 
    

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
