
from django import forms
from django.utils import timezone

from .models import MaintenanceHistory


class MaintenanceUpdateForm(forms.ModelForm):

    attachment = forms.FileField(
        required=False,
        help_text="Upload a maintenance photo or report"
    )

    class Meta:
        model = MaintenanceHistory

        fields = [
            "completed_date",
            "remarks",
        ]

        widgets = {
            "completed_date": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d"
            ),

            "remarks": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def clean_completed_date(self):

        completed_date = self.cleaned_data[
            "completed_date"
        ]

        if completed_date > timezone.localdate():
            raise forms.ValidationError(
                "Completion date cannot be in the future."
            )

        return completed_date
