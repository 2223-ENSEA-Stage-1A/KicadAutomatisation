# Generated by Django 4.2.2 on 2023-06-23 13:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myapp', '0006_remove_resultfile_selected'),
    ]

    operations = [
        migrations.CreateModel(
            name='PanelFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.TextField(default='', max_length=100)),
                ('description', models.TextField(default='')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('panel_file', models.FileField(upload_to='Panels/')),
                ('uploaded_files', models.ManyToManyField(to='myapp.uploadedfile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
