# Generated by Django 4.2.2 on 2023-07-10 07:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0034_alter_modellist_error_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='panelfile',
            name='amount',
            field=models.IntegerField(default=0),
        ),
    ]
