
from django.db import models
from django.conf import settings
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.core.validators import MinValueValidator

# Auto-generated service rules: equipment type -> (task type, interval in months)
SERVICE_RULES = {
    "DEG": ("DEG", 9),   # DEG service every 9 months
    "AC":  ("AC", 3),    # AC service every 3 months
    "BAT": ("BAT", 4),   # Battery test every 4 months
}


class Site(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)
    location = models.CharField(max_length=255, blank=True)

    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="sites",
        blank=True,
    )

    def __str__(self):
        return self.name


class Equipment(models.Model):

    TYPES = [
        ("DEG", "Diesel Generator"),
        ("AC", "Air Conditioner"),
        ("BAT", "Battery Bank"),
    ]

    equipment_id = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(max_length=150)

    equipment_type = models.CharField(
        max_length=10,
        choices=TYPES
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT
    )

    active = models.BooleanField(default=True)

    make = models.CharField(max_length=100, blank=True)
    tank_capacity_litres = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Generators only",
    )

    def __str__(self):
        return self.equipment_id
    
    


class MaintenanceSchedule(models.Model):

    TASKS = [
        ("DEG", "DEG Service"),
        ("AC", "AC Service"),
        ("DEG_Faul", "DEG Fault"),
        ("AC_Faul", "AC Fault"),
        ("BAT", "Battery Test"),
    ]

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.PROTECT
    )

    task_type = models.CharField(
        max_length=10,
        choices=TASKS
    )

    interval_months = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    last_completed = models.DateField()

    next_due = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["equipment", "task_type"],
                name="unique_equipment_task"
            )
        ]

    def save(self, *args, **kwargs):

        self.next_due = (
            self.last_completed
            + relativedelta(months=self.interval_months)
        )

        super().save(*args, **kwargs)

    @property
    def status(self):

        from django.utils import timezone

        remaining = (
            self.next_due - timezone.localdate()
        ).days

        if remaining < 0:
            return "Overdue"

        if remaining == 0:
            return "Due Today"

        if remaining <= 15:
            return "Due Soon"

        return "On Track"

    def __str__(self):
        return (
            f"{self.equipment.equipment_id} "
            f"- {self.get_task_type_display()}"
        )


class MaintenanceHistory(models.Model):

    schedule = models.ForeignKey(
        MaintenanceSchedule,
        on_delete=models.PROTECT,
        related_name="history"
    )

    completed_date = models.DateField()

    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )


class MaintenanceAttachment(models.Model):

    history = models.ForeignKey(
        MaintenanceHistory,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    file = models.FileField(
        upload_to="maintenance/%Y/%m/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )



class DieselFilling(models.Model):

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="diesel_fills",
        limit_choices_to={"equipment_type": "DEG"},
    )
    filled_date = models.DateField()
    litres = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    running_hours = models.DecimalField(
        max_digits=9, decimal_places=1, null=True, blank=True,
        help_text="Generator hour meter reading (optional)",
    )
    remarks = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-filled_date", "-id"]


    tank_level_after = models.DecimalField(
    max_digits=8, decimal_places=2, null=True, blank=True,
    validators=[MinValueValidator(0)],
    help_text="Litres in the tank after filling (from dipstick or gauge)",)

    def __str__(self):
        return f"{self.equipment} - {self.litres} L on {self.filled_date}"