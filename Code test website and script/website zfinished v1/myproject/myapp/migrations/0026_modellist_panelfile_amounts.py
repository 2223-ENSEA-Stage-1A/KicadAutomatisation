# Generated by Django 4.2.2 on 2023-07-06 09:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0025_panelfile_kicad_pcb_panelfile_zippeddrills_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModelList',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('error_names', models.TextField(unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='panelfile',
            name='amounts',
            field=models.OneToOneField(default=None, on_delete=django.db.models.deletion.CASCADE, to='myapp.modellist'),
        ),
    ]