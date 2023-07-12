from django import forms
from .models import PanelFile, UploadedFile, Ticket, Message
from multiupload.fields import MultiFileField, MultiMediaField, MultiImageField
from django.contrib.auth.models import User
from .models import ResultFile


class DepositForm(forms.Form):
    description = forms.CharField(max_length=100)
    file = forms.FileField()

    class Meta:
        model = UploadedFile
        fields = ('file', 'description')


class GerberUploadForm(forms.Form):
    gerber_files = MultiFileField(max_num=10, min_num=1)


class TicketForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        result_file_id = kwargs.pop('result_file_id', None)
        panel_file_id_tmp = kwargs.pop('panel_file_id', None)
        if panel_file_id_tmp:
            if type(panel_file_id_tmp) == int:
                panel_file_id = [panel_file_id_tmp]
            else:
                panel_file_id = []
                [panel_file_id.append(x) for x in panel_file_id_tmp if not x in panel_file_id]
        else:
            panel_file_id = None
        print(panel_file_id)

        super().__init__(*args, **kwargs)

        if user and self.instance.pk:
            self.fields['co_users'].queryset = User.objects.exclude(id=user.id)
        self.fields['result_file'].queryset = ResultFile.objects.filter(user=user)
        self.fields['panel_file'].queryset = PanelFile.objects.filter(result_files__user=user).distinct()

        if result_file_id:
            self.fields['result_file'].initial = result_file_id
        
        if panel_file_id:
            self.fields['panel_file'].initial = panel_file_id

    co_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.SelectMultiple,
        required=False
    )

    result_file = forms.ModelChoiceField(
        queryset=ResultFile.objects.all(),  # Use .all() to retrieve all ResultFile objects
        label='Result File',
        required=False
    )

    panel_file = forms.ModelChoiceField(
        queryset=PanelFile.objects.all(),  # Use .all() to retrieve all ResultFile objects
        label='Panel File',
        required=False
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'result_file', 'panel_file', 'co_users']

class StaffResponseForm(forms.Form):
    response = forms.CharField(widget=forms.Textarea)


class ResultFileForm(forms.ModelForm):
    uploaded_file = forms.FileField()
    description = forms.CharField(widget=forms.Textarea)

    class Meta:
        model = ResultFile
        fields = []  # Exclude all other fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.uploaded_file:
            self.fields['uploaded_file'].initial = self.instance.uploaded_file.file
            self.fields['description'].initial = self.instance.description


class PanelFileForm(forms.ModelForm):
    result_files = forms.ModelMultipleChoiceField(queryset=ResultFile.objects.all())

    class Meta:
        model = PanelFile
        fields = ['filename', 'description', 'result_files', 'amounts']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.result_files.exists():
            self.fields['result_files'].initial = self.instance.result_files.all()


class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter your message'}),
        label='Message'
    )
    
    class Meta:
        model = Message
        fields = ['content']

class DRCForm(forms.Form):
    def __init__(self, drc_types, *args, **kwargs):
        super(DRCForm, self).__init__(*args, **kwargs)
        for drc_type in drc_types:
            self.fields[f'{drc_type}'] = forms.BooleanField(required=False, label=drc_type)