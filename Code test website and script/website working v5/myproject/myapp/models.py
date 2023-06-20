from django.db import models
from django.contrib.auth.models import User

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
    description = models.TextField(default='')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.TextField(max_length=100, default='')

