from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework.authtoken.views import obtain_auth_token
from django_rest_passwordreset.views import (
    reset_password_request_token,
)

from rest_framework.schemas import get_schema_view
from . import views

urlpatterns = [
    path("users/", views.UsersEndpoint.as_view(), name="users"),
    path('users/<uuid:pk>/', views.UserEndpoint.as_view(), name='user_details'),
    path("users/login/", views.CustomAuthToken.as_view(), name="users_login"),
    path('users/verify/', views.UserVerify.as_view(), name='users_verify'),
    path('reset_password/', reset_password_request_token, name="reset_password_request_token"),
    path('reset_password/confirm/', views.CustomResetPasswordConfirm.as_view(), name="reset_password_confirm"),
    path('users/me/change-password/', views.ChangePasswordEndpoint.as_view(), name="change_password"),
    path("stores/", views.StoresEndpoint.as_view(), name="stores"),
    path("stores/<uuid:pk>/", views.StoreEndpoint.as_view(), name="store_details"),
    path("stores/<uuid:pk>/profit-report/", views.StoreProfitReportEndpoint.as_view(), name="store_profit_report"),
    path("stores/<uuid:pk>/orders-report/", views.StoreOrdersReportEndpoint.as_view(), name="store_orders_report"),
    path("stores/<uuid:pk>/stock-report/", views.StoreProductStocksReportEndpoint.as_view(), name="store_stock_report"),
    path("stores/<uuid:pk>/admins/", views.StoreAdminsEndpoint.as_view(), name="store_admins"),
    path("stores/<uuid:pk>/customers/", views.StoreCustomersEndpoint.as_view(), name="store_customers"),
    path("stores/<uuid:pk>/products/", views.StoreProductsEndpoint.as_view(), name="store_products"),
    path("stores/<uuid:pk>/orders/", views.StoreOrdersEndpoint.as_view(), name="store_orders"),
    path("customers/", views.CustomersEndpoint.as_view(), name="customers"),
    path("customers/<uuid:pk>/", views.CustomerEndpoint.as_view(), name="customer_details"),
    path("customers/<uuid:pk>/orders/", views.CustomerOrdersEndpoint.as_view(), name="customer_orders"),
    path("customers/<uuid:pk>/ordered-products/", views.CustomerOrderedProductsEndpoint.as_view(), name="customer_ordered_products"),
    path("products/", views.ProductsEndpoint.as_view(), name="products"),
    path("products/<uuid:pk>/", views.ProductEndpoint.as_view(), name="product_details"),
    path("products/<uuid:pk>/stocks/", views.ProductProductStocksEndpoint.as_view(), name="product_product_stocks"),
    path("products/<uuid:pk>/customers/", views.ProductCustomersEndpoint.as_view(), name="product_customers"),
    path("product-stocks/", views.ProductStocksEndpoint.as_view(), name="product_stocks"),
    path("product-stocks/<uuid:pk>/", views.ProductStockEndpoint.as_view(), name="product_stock_details"),
    path("orders/", views.OrdersEndpoint.as_view(), name="orders"),
    path("orders/<uuid:pk>/", views.OrderEndpoint.as_view(), name="order_details"),
    path("orders/<uuid:pk>/order-items/", views.OrderOrderItemsEndpoint.as_view(), name="order_order_items"),
    path("orders/<uuid:pk>/payments/", views.OrderPaymentsEndpoint.as_view(), name="order_payments"),
    path("order-items/", views.OrderItemsEndpoint.as_view(), name="order_items"),
    path("order-item/<uuid:pk>/", views.OrderItemEndpoint.as_view(), name="order_item_details"),
    path("payments/", views.PaymentsEndpoint.as_view(), name="payments"),
    path("payments/<uuid:pk>/", views.PaymentEndpoint.as_view(), name="payment_details"),
]
