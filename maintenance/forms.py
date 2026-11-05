
from django import forms
from django.utils import timezone

from .models import MaintenanceHistory, DieselFilling



class MaintenanceUpdateForm(forms.ModelForm):

    attachment = forms.FileField(
        required=False, 
        help_text="Upload a maintenance photo or report")

    class Meta:
        model = MaintenanceHistory
        fields = ["completed_date","remarks",]

        widgets = {
            "completed_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d"
            ),
            "remarks": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_completed_date(self):

        completed_date = self.cleaned_data["completed_date"]
        if completed_date > timezone.localdate():
            raise forms.ValidationError(
                "Completion date cannot be in the future."
            )

        return completed_date
    



class DieselFillingForm(forms.ModelForm):

    class Meta:
        model = DieselFilling
        fields = ["filled_date", "litres", "tank_level_after", "running_hours", "remarks"]
        widgets = {
            "filled_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, equipment=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.equipment = equipment

    def clean_filled_date(self):
        d = self.cleaned_data["filled_date"]
        if d > timezone.localdate():
            raise forms.ValidationError("Filling date cannot be in the future.")
        return d

    def clean(self):
        cleaned = super().clean()
        if not self.equipment:
            return cleaned

        litres = cleaned.get("litres")
        level = cleaned.get("tank_level_after")
        hours = cleaned.get("running_hours")
        filled_date = cleaned.get("filled_date")
        capacity = self.equipment.tank_capacity_litres

        # Tank level checks
        if level is not None:
            if capacity and level > capacity:
                self.add_error(
                    "tank_level_after",
                    f"Tank level cannot be more than the tank capacity "
                    f"({capacity:.0f} L).",
                )
            if litres is not None and level < litres:
                self.add_error(
                    "tank_level_after",
                    "Tank level after filling cannot be less than the "
                    "litres you added.",
                )

        # Litres added cannot exceed the tank size
        if litres is not None and capacity and litres > capacity:
            self.add_error(
                "litres",
                f"Litres added cannot be more than the tank capacity "
                f"({capacity:.0f} L).",
            )

        # Running hours must not go backwards
        if hours is not None and filled_date:
            previous = (
                self.equipment.diesel_fills
                .filter(running_hours__isnull=False,
                        filled_date__lte=filled_date)
                .order_by("-filled_date", "-id")
                .first()
            )
            if previous and hours < previous.running_hours:
                self.add_error(
                    "running_hours",
                    f"Running hours cannot be lower than the previous "
                    f"reading ({previous.running_hours}).",
                )

        return cleaned