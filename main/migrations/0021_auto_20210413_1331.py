# Generated by Django 2.2.5 on 2021-04-13 13:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_auto_20210406_1824'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customer',
            name='email',
            field=models.EmailField(blank=True, default=None, max_length=254, null=True, verbose_name='Email'),
        ),
    ]
