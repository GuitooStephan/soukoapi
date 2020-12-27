# Generated by Django 2.2.5 on 2020-12-17 00:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_auto_20201216_2220'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='total_amount',
        ),
        migrations.AddField(
            model_name='orderitem',
            name='cost',
            field=models.FloatField(blank=True, default=0.0, null=True),
        ),
    ]
