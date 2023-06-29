from django.db import models
from django.contrib.auth.models import User
import json

class UploadedFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/')
    description = models.TextField(default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.TextField(max_length=100, default='')

class ResultFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, default=None)
    zippedGerbers = models.FileField(upload_to='uploads/')
    zippedDrills = models.FileField(upload_to='uploads/')
    DRCresult = models.FileField(upload_to='uploads/')
    ERCresult = models.FileField(upload_to='uploads/')
    description = models.TextField(max_length=100, default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.TextField(max_length=100, default='')
    valid = models.BooleanField(default=False)

    def __str__(self):
        return self.filename

class PanelFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    filename = models.TextField(max_length=100, default='') 
    description = models.TextField(default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_files = models.ManyToManyField(UploadedFile)
    panel_file = models.FileField(upload_to='Panels/')
     
    def __str__(self):
        return self.filename

class Ticket(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    staff_response = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    co_users = models.ManyToManyField(User, related_name='co_tickets', blank=True)
    reopened = models.BooleanField(default=False)
    reopen_requested = models.BooleanField(default=False)
    result_file = models.OneToOneField(ResultFile, on_delete=models.CASCADE, blank=True, null=True, default=None)
    panel_file = models.OneToOneField(PanelFile, on_delete=models.CASCADE, blank=True, null=True, default=None)

    def __str__(self):
        return self.title
    
class Message(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    answeredByStaff = models.BooleanField(default=False)

    def __str__(self):
        return self.content

class AuthorizedError(models.Model):
    error_names = models.TextField(unique=True)

    def get_error_names(self):
        return json.loads(self.error_names)

    def set_error_names(self, error_names):
        self.error_names = json.dumps(error_names)

    authorized_error_names = property(get_error_names, set_error_names)
