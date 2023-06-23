from django import forms
from .models import UploadedFile
from multiupload.fields import MultiFileField, MultiMediaField, MultiImageField

class DepositForm(forms.Form):
    description = forms.CharField(max_length=100)
    file = forms.FileField()

    class Meta:
        model = UploadedFile
        fields = ('file', 'description')


class GerberUploadForm(forms.Form):
    gerber_files = MultiFileField(max_num=10, min_num=1)

