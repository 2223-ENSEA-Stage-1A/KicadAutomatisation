# Generated by Django 4.2.2 on 2023-06-30 09:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0024_remove_panelfile_uploaded_files_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='panelfile',
            name='kicad_pcb',
            field=models.FileField(default='zzccmxtp.zip', upload_to='uploads/'),
        ),
        migrations.AddField(
            model_name='panelfile',
            name='zippedDrills',
            field=models.FileField(default='zzccmxtp.zip', upload_to='uploads/'),
        ),
        migrations.AddField(
            model_name='panelfile',
            name='zippedGerbers',
            field=models.FileField(default='zzccmxtp.zip', upload_to='uploads/'),
        ),
    ]
