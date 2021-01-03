import json
import datetime
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

from django_rest_passwordreset.models import (
    ResetPasswordToken,
)

from rest_framework import status
from rest_framework.test import APIClient

from django.test import TestCase
from django.conf import settings
from django.urls import reverse, resolve
from django.contrib.auth import get_user_model

from .utils.auth_utils import generate_jwt_token
from .generators import (
    generate_verification_code
)
from .models import (
    VerificationCode,
    Category,
    Admin,
    Store,
    Customer,
    Product,
    Order,
    OrderItem,
    ProductStock,
    Payment,
    OrdersTimestampedMetric
)

User = get_user_model()

class AuthenticationTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.user_two = User.objects.create_user(**{
            'email': 'steph@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.reset_password_token = ResetPasswordToken.objects.create(
            user=self.user_two,
            user_agent='',
            ip_address='',
        )

        self.code = VerificationCode.objects.create(**{
            'email': self.user.email,
            'code': generate_verification_code()
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    @patch("api.views.send_email_async.delay")
    def test_user_signup(self, send_email_async):
        send_email_async.return_value = Mock()
        payload = {
            'email' : 'guystephane00@gmail.com',
            'password' : '2_Password',
            'first_name' : 'Guy',
            'username': 'guy_tanoh',
            'last_name' : 'Tanoh',
            'dob': '{}'.format(datetime.datetime(1994,3,31).strftime(settings.DATE_FORMAT))
        }

        response = self.client.post(
            reverse('users'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(send_email_async.call_count, 1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        send_email_async.assert_called()

    def test_user_login(self):
        client = APIClient()

        payload = {
            'email' : 'guy@ampersandllc.co',
            'password' : '2Password_'
        }

        response = client.post(
            reverse('users_login'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_users_verify_after_signup(self):
        response = self.client.get(
            f"{reverse('users_verify')}?code={self.code.code}",
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    @patch("main.signals.send_email_async.delay")
    def test_reset_password(self, send_email_async):
        send_email_async.return_value = Mock()
        payload = {
            'email': str(self.user.email)
        }

        response = self.client.post(
            reverse('reset_password_request_token'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(send_email_async.call_count, 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_email_async.assert_called()

    def test_user_reset_password_confirm(self):
        payload = {
            'password': '2Password_',
            'token': self.reset_password_token.key
        }
        response = self.client.post(
            reverse('reset_password_confirm'),
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_change_password(self):
        payload = {
            'old_password': '2Password_',
            'new_password': '2_Password_'
        }
        response = self.client.post(
            reverse('change_password'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user(self):
        response = self.client.get(
            reverse('user_details', kwargs={'pk': self.user.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user(self):
        payload = {
            'first_name': 'Stephane',
            'last_name': 'John'
        }

        response = self.client.put(
            reverse('user_details', kwargs={'pk': self.user.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StoreTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.user_two = User.objects.create_user(**{
            'email': 'steph@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.user_three = User.objects.create_user(**{
            'email': 'stephane@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'Stephane',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.category_shoes = Category.objects.create(**{
            'name': 'Shoes'
        })

        self.category_clothes = Category.objects.create(**{
            'name': 'Clothes'
        })

        self.store = Store.objects.create(**{
            'name': 'Noir Life',
            'phone_number': '+233209456202'
        })

        self.store.categories.set( [ self.category_shoes ] )

        self.admin = Admin.objects.create(**{
            'user': self.user_three,
            'store': self.store,
            'role': 'OWNER'
        })

        self.admin_two = Admin.objects.create(**{
            'user': self.user_two,
            'role': 'ADMIN'
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_create_store(self):
        payload = {
            'user_id': str(self.user.pk),
            'name': 'Guitoo Studios',
            'phone_number': '+233209456202',
            'city': 'Accra',
            'country': 'GH',
            'instagram_handle': '@guitooStudios',
            'categories_ids': [str(self.category_shoes.pk)]
        }

        response = self.client.post(
            reverse('stores'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fetch_stores(self):
        response = self.client.get(
            reverse('stores'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_store(self):
        response = self.client.get(
            reverse('store_details', kwargs={'pk': self.store.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_store(self):
        payload = {
            'categories_ids': [ str(self.category_clothes.pk) ],
            'admins_ids': [ str(self.admin_two.pk) ]
        }

        response = self.client.put(
            reverse('store_details', kwargs={'pk': self.store.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_store_admins(self):
        response = self.client.get(
            reverse('store_admins', kwargs={'pk': self.store.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CustomerTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.user_two = User.objects.create_user(**{
            'email': 'steph@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.category_shoes = Category.objects.create(**{
            'name': 'Shoes'
        })

        self.category_clothes = Category.objects.create(**{
            'name': 'Clothes'
        })

        self.store = Store.objects.create(**{
            'name': 'Noir Life',
            'phone_number': '+233209456202'
        })

        self.store_two = Store.objects.create(**{
            'name': 'Noir Thing',
            'phone_number': '+233209456202'
        })

        self.store.categories.set( [ self.category_shoes ] )

        self.admin = Admin.objects.create(**{
            'user': self.user,
            'store': self.store,
            'role': 'OWNER'
        })

        self.customer = Customer.objects.create(**{
            'store': self.store,
            'first_name': 'Guitoo',
            'last_name': 'Steph',
            'email': 'something@something.com'
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_create_customer(self):
        payload = {
            'store_id': str(self.store_two.pk),
            'first_name': 'Guitoo',
            'last_name': 'Stephan',
            'phone_number': '+233209456202',
            'city': 'Accra',
            'email': 'somethig@something.com',
            'country': 'GH',
            'address': 'BP 21 Bonoua'
        }

        response = self.client.post(
            reverse('customers'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fetch_customers(self):
        response = self.client.get(
            reverse('customers'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_store_customers(self):
        response = self.client.get(
            reverse('store_customers', kwargs={'pk': self.store.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_customer(self):
        response = self.client.get(
            reverse('customer_details', kwargs={'pk': self.customer.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_customer(self):
        payload = {
            'first_name': 'Gustave'
        }

        response = self.client.put(
            reverse('customer_details', kwargs={'pk': self.customer.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProductTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.user_two = User.objects.create_user(**{
            'email': 'steph@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.category_shoes = Category.objects.create(**{
            'name': 'Shoes'
        })

        self.category_clothes = Category.objects.create(**{
            'name': 'Clothes'
        })

        self.store = Store.objects.create(**{
            'name': 'Noir Life',
            'phone_number': '+233209456202'
        })

        self.store_two = Store.objects.create(**{
            'name': 'Noir Thing',
            'phone_number': '+233209456202'
        })

        self.store.categories.set( [ self.category_shoes ] )

        self.admin = Admin.objects.create(**{
            'user': self.user,
            'store': self.store,
            'role': 'OWNER'
        })

        self.product = Product.objects.create(**{
            'store': self.store,
            'name': 'Goyard Bags',
            'buying_price': 170.0,
            'selling_price': 300.0
        })

        self.stock = ProductStock.objects.create(**{
            'product': self.product,
            'quantity': 9
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_create_product(self):
        payload = {
            'store_id': str(self.store_two.pk),
            'name': 'Gucci Bags',
            'quantity': 9,
            'buying_price': 150.0,
            'selling_price': 250.0
        }

        response = self.client.post(
            reverse('products'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fetch_products(self):
        response = self.client.get(
            reverse('products'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product_stock(self):
        payload = {
            'product_id': str(self.product.pk),
            'quantity': 10,
        }

        response = self.client.post(
            reverse('product_stocks'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fetch_product_stocks(self):
        response = self.client.get(
            reverse('product_stocks'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_store_products(self):
        response = self.client.get(
            reverse('store_products', kwargs={'pk': self.store.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_product_product_stocks(self):
        response = self.client.get(
            reverse('product_product_stocks', kwargs={'pk': self.product.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_product(self):
        response = self.client.get(
            reverse('product_details', kwargs={'pk': self.product.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_product(self):
        payload = {
            'name': 'Louis Vuitton Bags'
        }

        response = self.client.put(
            reverse('product_details', kwargs={'pk': self.product.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_product(self):
        response = self.client.delete(
            reverse('product_details', kwargs={'pk': self.product.pk}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_retrieve_product_stock(self):
        response = self.client.get(
            reverse('product_stock_details', kwargs={'pk': self.stock.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_product_stock(self):
        payload = {
            'quantity': 10
        }

        response = self.client.put(
            reverse('product_stock_details', kwargs={'pk': self.stock.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_product_stock(self):
        response = self.client.delete(
            reverse('product_stock_details', kwargs={'pk': self.stock.pk}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class OrderTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.category_shoes = Category.objects.create(**{
            'name': 'Shoes'
        })

        self.category_clothes = Category.objects.create(**{
            'name': 'Clothes'
        })

        self.store = Store.objects.create(**{
            'name': 'Noir Life',
            'phone_number': '+233209456202'
        })

        self.store.categories.set( [ self.category_shoes ] )

        self.admin = Admin.objects.create(**{
            'user': self.user,
            'store': self.store,
            'role': 'OWNER'
        })

        self.customer = Customer.objects.create(**{
            'store': self.store,
            'first_name': 'Guitoo',
            'last_name': 'Steph',
            'email': 'something@something.com'
        })

        self.product = Product.objects.create(**{
            'store': self.store,
            'name': 'Goyard Bags',
            'buying_price': 170.0,
            'selling_price': 50.0
        })

        self.stock = ProductStock.objects.create(**{
            'product': self.product,
            'quantity': 9
        })

        self.product_two = Product.objects.create(**{
            'store': self.store,
            'name': 'Gucci Bags',
            'buying_price': 170.0,
            'selling_price': 50.0
        })

        self.stock_two = ProductStock.objects.create(**{
            'product': self.product_two,
            'quantity': 9
        })

        self.order = Order.objects.create(**{
            'store': self.store,
            'customer': self.customer,
            'delivery_fee': 0.0
        })

        self.order_item = OrderItem.objects.create(**{
            'order': self.order,
            'product': self.product,
            'product_stock': self.stock,
            'quantity': 3
        })

        self.order_item_two = OrderItem.objects.create(**{
            'order': self.order,
            'product': self.product_two,
            'product_stock': self.stock_two,
            'quantity': 2
        })

        self.payment = Payment.objects.create(**{
            'order': self.order,
            'amount': 50.0
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_create_order(self):
        payload = {
            'store_id': str(self.store.pk),
            'customer_id': str(self.customer.pk),
            'delivery_fee': 0.0
        }

        response = self.client.post(
            reverse('orders'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_item(self):
        payload = {
            'order_id': str(self.order.pk),
            'product_id': str(self.product_two.pk),
            'quantity': 3
        }

        response = self.client.post(
            reverse('order_items'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_payment(self):
        payload = {
            'order_id': str(self.order.pk),
            'amount': 50.0
        }

        response = self.client.post(
            reverse('payments'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_payment_to_pay_in_full(self):
        payload = {
            'order_id': str(self.order.pk),
            'amount': 200.0
        }

        response = self.client.post(
            reverse('payments'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_item_with_cost(self):
        payload = {
            'order_id': str(self.order.pk),
            'product_id': str(self.product_two.pk),
            'quantity': 3,
            'cost': 130.0
        }

        response = self.client.post(
            reverse('order_items'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_order_item_and_exceeding_stock(self):
        payload = {
            'order_id': str(self.order.pk),
            'product_id': str(self.product_two.pk),
            'quantity': 10,
            'cost': 130.0
        }

        response = self.client.post(
            reverse('order_items'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_orders(self):
        response = self.client.get(
            reverse('orders'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fetch_payments(self):
        response = self.client.get(
            reverse('payments'),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_order_order_items(self):
        response = self.client.get(
            reverse('order_order_items', kwargs={'pk': self.order.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_order_payments(self):
        response = self.client.get(
            reverse('order_payments', kwargs={'pk': self.order.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_order(self):
        response = self.client.get(
            reverse('order_details', kwargs={'pk': self.order.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_order(self):
        payload = {
            'delivery_fee': 5.0
        }

        response = self.client.put(
            reverse('order_details', kwargs={'pk': self.order.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_order_item(self):
        response = self.client.get(
            reverse('order_item_details', kwargs={'pk': self.order_item.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_order_item(self):
        payload = {
            'quantity': 4,
            'cost': 200.0
        }

        response = self.client.put(
            reverse('order_item_details', kwargs={'pk': self.order_item.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_order_item(self):
        response = self.client.delete(
            reverse('order_item_details', kwargs={'pk': self.order_item.pk}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_retrieve_payment(self):
        response = self.client.get(
            reverse('payment_details', kwargs={'pk': self.payment.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_order_item(self):
        payload = {
            'amount': 70.0
        }

        response = self.client.put(
            reverse('payment_details', kwargs={'pk': self.payment.pk}),
            data=json.dumps(payload), content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_customer_orders(self):
        response = self.client.get(
            reverse('customer_orders', kwargs={'pk': self.customer.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_store_orders(self):
        response = self.client.get(
            reverse('store_orders', kwargs={'pk': self.store.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fetch_customer_ordered_products(self):
        response = self.client.get(
            reverse('customer_ordered_products', kwargs={'pk': self.customer.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fetch_products_customers(self):
        response = self.client.get(
            reverse('product_customers', kwargs={'pk': self.product.pk}),
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)



class ReportTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(**{
            'email': 'guy@ampersandllc.co',
            'password': '2Password_',
            'first_name' : 'Guy',
            'username': 'guitoo',
            'last_name' : 'Tanoh',
            'is_email_confirmed': True
        })

        self.category_shoes = Category.objects.create(**{
            'name': 'Shoes'
        })

        self.category_clothes = Category.objects.create(**{
            'name': 'Clothes'
        })

        self.store = Store.objects.create(**{
            'name': 'Noir Life',
            'phone_number': '+233209456202'
        })

        self.store.categories.set( [ self.category_shoes ] )

        self.admin = Admin.objects.create(**{
            'user': self.user,
            'store': self.store,
            'role': 'OWNER'
        })

        self.customer = Customer.objects.create(**{
            'store': self.store,
            'first_name': 'Guitoo',
            'last_name': 'Steph',
            'email': 'something@something.com'
        })

        self.product = Product.objects.create(**{
            'store': self.store,
            'name': 'Goyard Bags',
            'buying_price': 170.0,
            'selling_price': 300.0
        })

        self.stock = ProductStock.objects.create(**{
            'product': self.product,
            'quantity': 9
        })

        self.product_two = Product.objects.create(**{
            'store': self.store,
            'name': 'Gucci Bags',
            'buying_price': 170.0,
            'selling_price': 300.0
        })

        self.stock_two = ProductStock.objects.create(**{
            'product': self.product_two,
            'quantity': 9
        })

        self.order = Order.objects.create(**{
            'store': self.store,
            'customer': self.customer,
            'delivery_fee': 0.0,
            'payment_status': 'PAID'
        })

        self.order_item = OrderItem.objects.create(**{
            'order': self.order,
            'product': self.product,
            'product_stock': self.stock,
            'quantity': 5
        })

        self.order_item_two = OrderItem.objects.create(**{
            'order': self.order,
            'product': self.product_two,
            'product_stock': self.stock_two,
            'quantity': 2
        })

        self.payment = Payment.objects.create(**{
            'order': self.order,
            'amount': 2100.0
        })

        self.order_two = Order.objects.create(**{
            'store': self.store,
            'customer': self.customer,
            'delivery_fee': 0.0,
            'payment_status': 'PAID'
        })
        self.order_two.created_at = datetime.datetime(2020, 5, 17)
        self.order_two.save()

        self.order_item_order_two = OrderItem.objects.create(**{
            'order': self.order_two,
            'product': self.product,
            'product_stock': self.stock,
            'quantity': 3
        })

        self.payment_two = Payment.objects.create(**{
            'order': self.order_two,
            'amount': 900.0
        })

        self.orders_metric = OrdersTimestampedMetric.objects.create(**{
            'store': self.store,
            'orders': 2,
            'date': date.today()
        })

        self.orders_metric_two = OrdersTimestampedMetric.objects.create(**{
            'store': self.store,
            'orders': 0,
            'date': date.today() - timedelta(days=1)
        })

        self.client = APIClient()
        token = generate_jwt_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

    def test_profit_report(self):
        response = self.client.get(
            f"{reverse('store_profit_report', kwargs={'pk': self.store.pk})}?period=1",
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_orders_report(self):
        response = self.client.get(
            f"{reverse('store_orders_report', kwargs={'pk': self.store.pk})}?period=1",
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stock_report(self):
        response = self.client.get(
            f"{reverse('store_stock_report', kwargs={'pk': self.store.pk})}?period=1",
            content_type='application/json'
        )
        results = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)