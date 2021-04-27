# Generated by Django 2.2.5 on 2021-04-26 21:22

from django.db import migrations

from main import constants

def create_subscription_for_exiting_store(apps, schema_editor):
    Store = apps.get_model('main', 'Store')
    StoreSubscription = apps.get_model('main', 'StoreSubscription')
    Plan = apps.get_model('main', 'SubscriptionPlan')
    for store in Store.objects.all():
        if not StoreSubscription.objects.filter( store=store ).exists():
            StoreSubscription.objects.create(
                store=store,
                plan=Plan.objects.get(plan_type=constants.FREE_PLAN)
            )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_auto_20210426_2116'),
    ]

    operations = [
        migrations.RunPython(create_subscription_for_exiting_store),
    ]
