from django import forms

from .document_validation import validate_document_upload
from .models import Document


class DocumentAdminForm(forms.ModelForm):
    """Validate uploads before Django writes the file to private storage."""

    class Meta:
        model = Document
        fields = ("title", "file")

    def clean_file(self):
        upload = self.cleaned_data.get("file")
        if upload:
            validate_document_upload(upload)
        return upload
