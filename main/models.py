# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import pytz
import os
import uuid
import json
import pydash
import datetime
from datetime import timedelta, timezone
from functools import reduce

from django_celery_beat.models import PeriodicTask, CrontabSchedule
from django_celery_beat.managers import PeriodicTaskManager

from django.db import models
from django.utils import timezone as dj_timezone
from django.contrib.auth.models import BaseUserManager, AbstractUser
from django.db.models import (
    Q,
    F,
    Sum,
    Value
)
from django.db.models.functions import (
    Coalesce,
    Concat,
)

from phonenumber_field.modelfields import PhoneNumberField
from django_countries.fields import CountryField

from .generators import generate_verification_code
from . import constants

class UniqueNameFileField(models.ImageField):
    def generate_filename(self, instance, filename):
        _, ext = os.path.splitext(filename)
        name = f"{uuid.uuid4().hex}{ext}"
        return super().generate_filename(instance, name)

class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)

class User(AbstractUser):
    id = models.UUIDField(
        verbose_name='User Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    username = models.CharField(
        max_length=255,
        default=None,
        blank=True,
        null=True,
        unique=False
    )

    first_name = models.CharField(
        verbose_name='First Name',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    last_name = models.CharField(
        verbose_name='Last Name',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    email = models.EmailField(
        verbose_name='Email',
        max_length=254,
        blank=False,
        null=False,
        unique=True
    )

    dob = models.DateTimeField(
        verbose_name='Date of birth',
        null=True,
        blank=True
    )

    is_email_confirmed = models.BooleanField(
        verbose_name='Has email been confirmed',
        default=False
    )

    is_active: bool = models.BooleanField(default=True, db_index=True)

    is_onboarded: bool = models.BooleanField(default=False)

    timezone: str = models.CharField(
        max_length=40, default="utc", null=True, blank=True
    )

    required_change_password: bool = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return f"{ self.first_name } { self.last_name }"

    def get_full_name(self):
        """Return user's full name."""
        if self.last_name is not None:
            return """{} {}""".format(
                self.first_name, self.last_name
            ).strip()
        else:
            return self.first_name

    def get_short_name(self):
        """Return user's first name."""
        return self.first_name

    class Meta:
        ordering = ('id',)
        verbose_name_plural = 'users'
        unique_together = ('id', 'username',)


class VerificationCode(models.Model):
    email = models.EmailField()

    code = models.CharField(max_length=6, default=generate_verification_code)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Verification Code for { self.email }"


class Category(models.Model):
    id = models.UUIDField(
        verbose_name='Category Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=255,
        blank=False,
        null=False,
        verbose_name='Category name'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return '%s' % (self.name)


class Store(models.Model):
    id = models.UUIDField(
        verbose_name='Store Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    logo_url = UniqueNameFileField(blank=True, null=True)

    name = models.CharField(
        verbose_name='Name',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    phone_number = PhoneNumberField(null=True, blank=True)

    categories = models.ManyToManyField(
        Category,
        related_name='stores',
        blank=True
    )

    city = models.CharField(
        verbose_name='City',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    country = CountryField(default="GH")

    instagram_handle = models.CharField(
        verbose_name='Instagram Handle',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    facebook_handle = models.CharField(
        verbose_name='Facebook Handle',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'stores'

    def get_profit_by_period( self, period=None ):
        if period not in [
            constants.LAST_WEEK,
            constants.LAST_MONTH,
            constants.LAST_YEAR,
            constants.ALL_TIME
        ]:
            raise Exception( "Time paramters must be 0 (for last week)) or 1 (for last month) or 2 (for last year) or 3 (for all time)" )
        
        if period == constants.LAST_WEEK:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=7)
            current_report = self._get_profit(start=start, end=end)
        elif period == constants.LAST_MONTH:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=30)
            current_report = self._get_profit(start=start, end=end)
        elif period == constants.LAST_YEAR:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end.replace(year=end.year - 1)
            current_report = self._get_profit(start=start, end=end)
        else:
            current_report = self._get_profit()

        return current_report

    def _get_profit( self, start=None, end=None ):
        _filter = None
        if start and end:
            _filter = Q(paid_on__range=[start, end])

        orders = Order.objects.filter(
            store=self,
            confirmed=True
        ).order_by("created_at") if not _filter else Order.objects.filter(
            _filter,
            store=self,
            confirmed=True
        ).order_by("created_at")

        return sum(o.profit for o in orders)


    def get_profit_report_by_period( self, period=None ):
        if period not in [
            constants.LAST_WEEK,
            constants.LAST_MONTH,
            constants.LAST_YEAR,
            constants.ALL_TIME
        ]:
            raise Exception( "Time paramters must be 0 (for last week)) or 1 (for last month) or 2 (for last year) or 3 (for all time)" )
        
        if period == constants.LAST_WEEK:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=7)
            current_report = self._get_profit_report(start=start, end=end)
        elif period == constants.LAST_MONTH:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=30)
            current_report = self._get_profit_report(start=start, end=end)
        elif period == constants.LAST_YEAR:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end.replace(year=end.year - 1)
            current_report = self._get_profit_report(start=start, end=end)
        else:
            current_report = self._get_profit_report()

        return current_report


    def _get_profit_report( self, start=None, end=None ):
        _filter = None

        queries = Q( store=self )

        if start and end:
            queries &= Q(date__range=[start, end])

        metrics = ProfitTimestampedMetric.objects.filter(
            queries
        ).order_by("date")

        return metrics.values("date", "profit")


    def get_orders_report_by_period( self, period=None ):
        if period not in [
            constants.LAST_WEEK,
            constants.LAST_MONTH,
            constants.LAST_YEAR,
            constants.ALL_TIME
        ]:
            raise Exception( "Time paramters must be 0 (for last week)) or 1 (for last month) or 2 (for last year) or 3 (for all time)" )
        
        if period == constants.LAST_WEEK:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=7)
            current_report = self._get_orders_report(start=start, end=end)
        elif period == constants.LAST_MONTH:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=30)
            current_report = self._get_orders_report(start=start, end=end)
        elif period == constants.LAST_YEAR:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end.replace(year=end.year - 1)
            current_report = self._get_orders_report(start=start, end=end)
        else:
            current_report = self._get_orders_report()

        return current_report

    def _get_orders_report( self, start=None, end=None ):
        _filter = None

        queries = Q( store=self )

        if start and end:
            queries &= Q(date__range=[start, end])

        metrics = OrdersTimestampedMetric.objects.filter(
            queries
        ).order_by("date")

        return metrics.values("date", "orders")

    def get_num_of_orders_report_by_period( self, period=None ):
        if period not in [
            constants.LAST_WEEK,
            constants.LAST_MONTH,
            constants.LAST_YEAR,
            constants.ALL_TIME
        ]:
            raise Exception( "Time paramters must be 0 (for last week)) or 1 (for last month) or 2 (for last year) or 3 (for all time)" )
        
        if period == constants.LAST_WEEK:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=7)
            current_report = self._get_num_of_orders_report(start=start, end=end)
        elif period == constants.LAST_MONTH:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=30)
            current_report = self._get_num_of_orders_report(start=start, end=end)
        elif period == constants.LAST_YEAR:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end.replace(year=end.year - 1)
            current_report = self._get_num_of_orders_report(start=start, end=end)
        else:
            current_report = self._get_num_of_orders_report()

        return current_report

    def _get_num_of_orders_report( self, start=None, end=None ):

        queries = Q( store=self )

        if start and end:
            queries &= Q(created_at__range=[start, end])

        all_orders = Order.objects.filter(
            queries,
            confirmed=True
        ).order_by("created_at")

        pending_orders = Order.objects.filter(
            queries,
            payment_status="PENDING",
            confirmed=True
        ).order_by("created_at")

        paid_orders = Order.objects.filter(
            queries,
            payment_status="PAID",
            confirmed=True
        ).order_by("created_at")

        return { 'number_of_orders': all_orders.count(), 'number_of_pending_orders': pending_orders.count(), 'number_of_paid_orders': paid_orders.count() }

    def get_low_products_stock( self ):
        products = Product.objects.filter(
            store=self
        ).order_by("created_at")

        stocks = map( lambda x: { 'id': x.id, "stock": x.get_total_stock() }, products )
        low_stock_products_list = filter( lambda x: x["stock"] < 3, list(stocks) )
        low_stock_products = Product.objects.filter( pk__in=[ s["id"] for s in list(low_stock_products_list) ] )

        return low_stock_products

    def get_best_selling_product_by_period( self, period=None ):
        if period not in [
            constants.LAST_WEEK,
            constants.LAST_MONTH,
            constants.LAST_YEAR,
            constants.ALL_TIME
        ]:
            raise Exception( "Time paramters must be 0 (for last week)) or 1 (for last month) or 2 (for last year) or 3 (for all time)" )
        
        if period == constants.LAST_WEEK:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=7)
            current_report = self._get_best_selling_product(start=start, end=end)
        elif period == constants.LAST_MONTH:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end - timedelta(days=30)
            current_report = self._get_best_selling_product(start=start, end=end)
        elif period == constants.LAST_YEAR:
            end = datetime.datetime.today().replace(tzinfo=pytz.utc)
            start = end.replace(year=end.year - 1)
            current_report = self._get_best_selling_product(start=start, end=end)
        else:
            current_report = self._get_best_selling_product()

        return current_report

    def _get_best_selling_product( self, start, end ):
        products = Product.objects.filter(
            store=self
        ).order_by("created_at")

        metrics = list( map( lambda x: { 'id': x.id, "num_bought": x.get_number_of_ordered_items_in_period(start, end) }, products ) )
        if len(metrics):
            _best_selling_product = pydash.max_by(list(metrics), "num_bought")
            product = Product.objects.get( pk=_best_selling_product["id"] )
            return product
        return None

    def __str__(self):
        return f"{ self.name }"


class Product(models.Model):
    id = models.UUIDField(
        verbose_name='Product Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    product_picture_url = UniqueNameFileField(blank=True, null=True)

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='products'
    )

    name = models.CharField(
        verbose_name='Name',
        default=None,
        max_length=255,
        blank=True,
        null=True
    )

    description = models.TextField(
        verbose_name='Description',
        default=None,
        blank=True,
        null=True
    )

    buying_price = models.FloatField(
        verbose_name='Buying / Production Price',
        blank=True, null=True, default=0.0
    )

    selling_price = models.FloatField(
        verbose_name='Selling Price',
        blank=True, null=True, default=0.0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('created_at',)
        verbose_name_plural = 'products'

    @property
    def current_stock(self):
        stocks = [x for x in self.stocks.all() if x.num_of_remaining_items > 0]
        stock = stocks[0] if len( stocks ) else self.stocks.filter( quantity__gt=0 ).first()
        return stock

    def get_total_stock(self):
        stocks = self.stocks.all()
        return reduce( lambda x, y : x + y, [ s.num_of_remaining_items for s in stocks ], 0 )

    def get_number_of_ordered_items_in_period(self, start=None, end=None):
        stocks = self.stocks.all()
        return reduce( lambda x, y : x + y, [ s.get_num_of_ordered_items_in_period(start, end) for s in stocks ], 0 )

    def __str__(self):
        return f"Product { self.name } from { self.store.name }"


class ProductStock(models.Model):
    id = models.UUIDField(
        verbose_name='Store Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='stocks'
    )

    quantity = models.IntegerField(blank=True, null=True, default=0)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('created_at',)
        verbose_name_plural = 'product_stocks'

    @property
    def num_of_ordered_items(self):
        return (
            self.order_items.all().aggregate(
                quantity_ordered= Coalesce( Sum( "quantity" ), Value("0") )
            ).get("quantity_ordered")
        )

    @property
    def num_of_remaining_items(self):
        return self.quantity - self.num_of_ordered_items

    def get_num_of_ordered_items_in_period(self, start=None, end=None):
        if start and end:
            return (
                self.order_items.filter( created_at__range=[start, end] ).aggregate(
                    quantity_ordered= Coalesce( Sum( "quantity" ), Value("0") )
                ).get("quantity_ordered")
            )
        else:
            return (
                self.order_items.all().aggregate(
                    quantity_ordered= Coalesce( Sum( "quantity" ), Value("0") )
                ).get("quantity_ordered")
            )

    def __str__(self):
        return f"Product Stock for Product { self.product.name }"


class Admin(models.Model):
    ROLES = [
        ('OWNER', 'Owner'),
        ('ADMIN', 'Admin')
    ]

    id = models.UUIDField(
        verbose_name='Admin Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='admin'
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='admins',
        null=True
    )

    role = models.CharField(
        verbose_name='Role',
        default=None,
        max_length=255,
        choices=ROLES,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('created_at',)
        verbose_name_plural = 'admins'

    # def __str__(self):
    #     return f"{self.store.name} admin - {self.user.first_name} {self.user.last_name}"


class Customer(models.Model):
    id = models.UUIDField(
        verbose_name='Customer Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='customers'
    )

    email = models.EmailField(
        verbose_name='Email',
        max_length=254,
        blank=False,
        null=False,
        unique=True
    )

    first_name = models.CharField(
        verbose_name='First Name',
        default=None,
        max_length=255,
        blank=True,
        null=True
    )

    last_name = models.CharField(
        verbose_name='Last Name',
        default=None,
        max_length=255,
        blank=True,
        null=True
    )

    dob = models.DateTimeField(
        verbose_name='Date of birth',
        null=True,
        blank=True
    )

    phone_number = PhoneNumberField(null=True, blank=True)

    city = models.CharField(
        verbose_name='City',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    country = CountryField(default="GH")

    address = models.CharField(
        verbose_name='Address',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    other_address_details = models.CharField(
        verbose_name='Other Address Details',
        max_length=255,
        default=None,
        blank=True,
        null=True
    )

    comment = models.TextField(
        verbose_name='Comment',
        default=None,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('created_at',)
        verbose_name_plural = 'customers'

    def get_ordered_products(self):
        return Product.objects.filter( order_items__order__customer__pk=self.pk ).distinct()

    def get_number_of_orders_for_product(self, product_id):
        order_items = OrderItem.objects.filter(
            order__customer=self,
            product__pk=product_id
        )
        return reduce( lambda x, y : x + y, [ o.quantity for o in order_items ], 0 )

    def get_number_of_orders(self):
        return self.orders.filter( confirmed=True ).count()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Order(models.Model):
    PAYMENT_STATUS = [
        ('PENDING', 'Not Paid'),
        ('PARTIALLY_PAID', 'Partially Paid'),
        ('PAID', 'Paid')
    ]

    id = models.UUIDField(
        verbose_name='Order Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='orders'
    )

    payment_status = models.CharField(
        verbose_name='Role',
        default='PENDING',
        max_length=255,
        choices=PAYMENT_STATUS,
        blank=True,
        null=True
    )

    paid_on = models.DateField( null=True, blank=True )

    delivery_fee = models.FloatField(blank=True, null=True, default=0.0)

    confirmed = models.BooleanField(
        verbose_name='Confirmed',
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('id',)
        verbose_name_plural = 'orders'

    @property
    def total_amount(self):
        return (
            self.order_items.all().aggregate(
                amount= Coalesce( Sum( "cost" ), Value("0") )
            ).get("amount") 
        )

    @property
    def amount_paid(self):
        return (
            self.payments.all().aggregate(
                amount_paid= Coalesce( Sum( "amount" ), Value("0.0") )
            ).get("amount_paid")
        )

    @property
    def balance(self):
        return self.total_amount - self.amount_paid

    @property
    def profit(self):
        return sum(i.profit for i in self.order_items.all())

    def get_number_of_products(self):
        return (
            self.order_items.all().aggregate(
                num_of_products= Coalesce( Sum( "quantity" ), Value("0") )
            ).get("num_of_products") 
        )

    def __str__(self):
        return f"Order from {self.store.name} by {self.customer.first_name} {self.customer.last_name}"


class OrderConfirmationCode(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='confirmation_code'
    )

    code = models.CharField(max_length=6, default=generate_verification_code)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Order Confirmation Code for { self.order.id }"


class OrdersTimestampedMetric(models.Model):
    id = models.UUIDField(
        verbose_name='Order Metrics Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='orders_metrics'
    )

    orders = models.IntegerField(default=0)

    date = models.DateField()

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return f"Metric: {self.date}, {self.store.pk}"


class StorePeriodicTaskManager(PeriodicTaskManager):
    def schedule_create_store_orders_metrics(self, store):
        schedule = CrontabSchedule.objects.create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*"
        )
        obj, created = self.get_or_create(
            store=store,
            crontab=schedule,
            name=f"Create store={store.id} orders report",
            task="main.tasks.create_store_orders_metrics",
            args=json.dumps([str(store.id)]),
            enabled=True,
        )
        return obj

    def schedule_create_store_profit_metrics(self, store):
        schedule = CrontabSchedule.objects.create(
            minute="*/5",
            hour="*",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*"
        )
        obj, created = self.get_or_create(
            store=store,
            crontab=schedule,
            name=f"Create store={store.id} profit report",
            task="main.tasks.create_store_profit_metrics",
            args=json.dumps([str(store.id)]),
            enabled=True,
        )
        return obj


class StorePeriodicTask(PeriodicTask):
    store = models.ForeignKey(
        Store, on_delete=models.CASCADE, related_name="+", null=True, blank=True
    )

    objects: StorePeriodicTaskManager = StorePeriodicTaskManager()


class ProfitTimestampedMetric(models.Model):
    id = models.UUIDField(
        verbose_name='Profit Metrics Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='profit_metrics'
    )

    profit = models.FloatField(blank=True, null=True, default=0.0)

    date = models.DateField()

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return f"Metric: {self.date}, {self.store.pk}"

class OrderItem(models.Model):
    id = models.UUIDField(
        verbose_name='Order Item Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='order_items'
    )

    product_stock = models.ForeignKey(
        ProductStock,
        on_delete=models.CASCADE,
        related_name='order_items',
        null=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='order_items'
    )

    quantity = models.IntegerField( default=0, blank=True, null=True )

    cost = models.FloatField( default=0.0, blank=True, null=True )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('id',)
        verbose_name_plural = 'order_items'

    @property
    def production_cost(self):
        return float( self.product.buying_price ) * float( self.quantity )

    @property
    def profit(self):
        return self.cost - self.production_cost

    def save(self, *args, **kwargs):
        if self.cost == 0.0:
            self.cost = self.quantity * self.product.selling_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order Item of Order {self.order.pk} of {self.product.name}"


class Payment(models.Model):
    id = models.UUIDField(
        verbose_name='Payment Id',
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    amount = models.FloatField( default=0.0, blank=True, null=True )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ('id',)
        verbose_name_plural = 'payments'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.order.balance <= float( 0 ):
            today = dj_timezone.now().date()
            self.order.payment_status = 'PAID'
            self.order.paid_on = today
            self.order.save()
        if self.order.balance > float( 0 ):
            self.order.payment_status = 'PARTIALLY_PAID'
            self.order.save()

    def __str__(self):
        return f"Payment of { self.order.pk } of {self.amount}"

