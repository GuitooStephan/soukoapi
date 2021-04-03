# Generated by Django 2.2.5 on 2021-03-14 13:44

from django.db import migrations, models
import django.db.models.deletion
import main.generators


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_auto_20210228_1259'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='confirmed',
            field=models.BooleanField(default=True, verbose_name='Confirmed'),
        ),
        migrations.CreateModel(
            name='OrderConfirmationCode',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(default=main.generators.generate_verification_code, max_length=6)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='confirmation_code', to='main.Order')),
            ],
        ),
    ]
