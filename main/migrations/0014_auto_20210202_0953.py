# Generated by Django 2.2.5 on 2021-02-02 09:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_customer_phone_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='payment_status',
            field=models.CharField(blank=True, choices=[('PENDING', 'Pending'), ('PARTIALLY_PAID', 'Partially Paid'), ('PAID', 'Paid')], default='PENDING', max_length=255, null=True, verbose_name='Role'),
        ),
    ]