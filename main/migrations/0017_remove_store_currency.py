# Generated by Django 2.2.5 on 2021-02-22 13:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0016_store_currency'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='store',
            name='currency',
        ),
    ]
