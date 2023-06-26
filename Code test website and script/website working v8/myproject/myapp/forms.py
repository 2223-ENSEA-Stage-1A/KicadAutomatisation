from django import forms
from .models import UploadedFile, Ticket, Message
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
        result_file_id = kwargs.pop('result_file_id', None)  # New line

        super().__init__(*args, **kwargs)

        if user and self.instance.pk:
            self.fields['co_users'].queryset = User.objects.exclude(id=user.id)
        self.fields['result_file'].queryset = ResultFile.objects.filter(user=user)

        if result_file_id:  # New lines
            self.fields['result_file'].initial = result_file_id

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

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'result_file', 'co_users']

class StaffResponseForm(forms.Form):
    response = forms.CharField(widget=forms.Textarea)

class MessageForm(forms.ModelForm):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Enter your message'}),
        label='Message'
    )
    
    class Meta:
        model = Message
        fields = ['content']