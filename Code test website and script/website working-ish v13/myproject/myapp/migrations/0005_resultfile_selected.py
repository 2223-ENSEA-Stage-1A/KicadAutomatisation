# Generated by Django 4.2.2 on 2023-06-21 06:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0004_resultfile_uploaded_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='resultfile',
            name='selected',
            field=models.BooleanField(default=False),
        ),
    ]
