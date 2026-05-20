"""Forms for the trainer app."""
from django import forms

from .models import PageSchema


class PageSchemaForm(forms.ModelForm):
    """Form for creating and updating page schemas."""

    class Meta:
        model = PageSchema
        fields = ("name", "description")
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Page name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Short description",
                    "rows": 5,
                }
            ),
        }
