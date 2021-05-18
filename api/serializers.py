from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import serializers

from main.models import (
    Store,
    Category,
    Admin,
    Customer,
    Product,
    Order,
    OrderItem,
    ProductStock,
    Payment,
    Subscriber,
    StoreSubscription,
    SubscriptionPlan
)

User = get_user_model()


class UserAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = (
            "id",
            "user_id",
            "store_id",
            "role",
            "created_at",
            "updated_at"
        )


class UserSerializer(serializers.ModelSerializer):
    dob = serializers.DateTimeField(format=settings.DATE_FORMAT, required=False)
    admin = UserAdminSerializer( read_only=True )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with email already exists")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "dob",
            "admin",
            "password",
            "is_staff",
            "timezone",
            "is_onboarded",
            "required_change_password",
            "is_active",
            "is_superuser",
            "is_email_confirmed",
        )
        extra_kwargs = {
            "password": {"write_only": True},
            "is_superuser": {"read_only": True},
            "is_staff": {"read_only": True},
        }


class SubscriberSerializer(serializers.ModelSerializer):
    def validate_email(self, value):
        if Subscriber.objects.filter(email=value).exists():
            raise serializers.ValidationError("Subscriber with email already exists")
        return value
    class Meta:
        model = Subscriber
        fields = "__all__"

class AuthTokenSerializer(serializers.Serializer):
    email = serializers.CharField(label=_("Email"), write_only=True)
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        trim_whitespace=False,
        write_only=True,
    )
    token = serializers.CharField(label=_("Token"), read_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(
                request=self.context.get("request"), username=email, password=password
            )

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            if not user:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs

class VerificationCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = (
            "id",
            "name"
        )

class AdminSerializer(serializers.ModelSerializer):
    user = UserSerializer( read_only=True )
    user_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='user',
        queryset=User.objects.all()
    )

    class Meta:
        model = Admin
        fields = (
            "id",
            "user",
            "user_id",
            "store_id",
            "role",
            "created_at",
            "updated_at"
        )


class SubscriptionPlanSerializer( serializers.ModelSerializer ):
    plan_type = serializers.SerializerMethodField( read_only=True )

    def get_plan_type(self, obj):
        return obj.get_plan_type_display()
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "plan_type",
            "period",
            "price",
            "products_limit",
            "orders_limit",
            "customers_limit",
            "created_at"
        )

class StoreSubscriptionSerializer( serializers.ModelSerializer ):
    plan = SubscriptionPlanSerializer( read_only=True )

    class Meta:
        model = StoreSubscription
        fields = (
            "id",
            "plan",
            "channel",
            "expires_at",
            "is_active",
            "is_cancelled",
            "needs_renewal",
            "created_at"
        )


class StoreSerializer( serializers.ModelSerializer ):
    categories = CategorySerializer(many=True, read_only=True)
    categories_ids = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source="categories",
        many=True,
        queryset=Category.objects.all(),
        required=False,
    )
    admins = AdminSerializer(many=True, read_only=True)
    admins_ids = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source="admins",
        many=True,
        required=False,
        queryset=Admin.objects.all()
    )
    compressed_logo_url = serializers.SerializerMethodField( read_only=True )
    my_subscription = StoreSubscriptionSerializer( read_only=True )


    def get_compressed_logo_url(self, obj):
        return f"https://{settings.AWS_S3_COMPRESSED_IMAGES_DOMAIN}/{obj.logo_url.name}" if obj.logo_url else ""

    class Meta:
        model = Store
        fields = "__all__"

    def update(self, instance, validated_data):
        categories = validated_data.pop("categories", None)
        admins = validated_data.pop("admins", None)

        store = super().update(instance, validated_data)

        if categories is not None:
            store.categories.set( categories )

        if admins is not None:
            store.admins.set( admins )
        return store


class SimpleStoreSerializer( serializers.ModelSerializer ):
    categories = CategorySerializer(many=True, read_only=True)

    compressed_logo_url = serializers.SerializerMethodField( read_only=True )


    def get_compressed_logo_url(self, obj):
        print( obj.logo_url )
        return f"https://{settings.AWS_S3_COMPRESSED_IMAGES_DOMAIN}/{obj.logo_url.name}" if obj.logo_url else ""

    class Meta:
        model = Store
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    store = StoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )

    def validate(self, data):
        if Customer.objects.filter(email=data['email'], store=data['store'].id).exists():
            raise serializers.ValidationError("Store customer with email already exists")
        return data

    class Meta:
        model = Customer
        fields = ("__all__")


class EditCustomerSerializer(serializers.ModelSerializer):
    store = StoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )

    def validate(self, data):
        if data.get( 'email' ) :
            instance = getattr(self, 'instance', None)
            if Customer.objects.exclude(pk=instance.pk).filter(email=data['email'], store=instance.store.id).exists():
                raise serializers.ValidationError("Store customer with email already exists")
        return data

    class Meta:
        model = Customer
        fields = ("__all__")


class ProductCustomerSerializer(serializers.ModelSerializer):
    store = StoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )
    num_of_orders = serializers.SerializerMethodField()

    def get_num_of_orders(self, obj):
        return obj.get_number_of_orders_for_product( self.context.get('view').kwargs.get('pk') )

    class Meta:
        model = Customer
        fields = ("__all__")
        read_only_fields = ("num_of_orders",)


class StoreCustomerSerializer(serializers.ModelSerializer):
    number_of_orders = serializers.SerializerMethodField()

    def get_number_of_orders(self, obj):
        return obj.get_number_of_orders()
    class Meta:
        model = Customer
        fields = ("__all__")
        read_only_fiels = ( "number_of_orders", )


class ProductStockSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='product',
        queryset=Product.objects.all()
    )

    class Meta:
        model = ProductStock
        fields = (
            "id",
            "product",
            "product_id",
            "quantity",
            "num_of_ordered_items",
            "num_of_remaining_items",
            "created_at"
        )
        read_only_fields = ( "product", )


class ProductSerializer(serializers.ModelSerializer):
    store = StoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )
    current_stock = ProductStockSerializer( read_only=True )
    stocks = ProductStockSerializer( read_only=True, many=True )
    total_stock = serializers.SerializerMethodField()
    num_of_orders =serializers.SerializerMethodField()
    compressed_product_picture_url = serializers.SerializerMethodField( read_only=True )
    is_active = serializers.BooleanField( default=True )

    def get_total_stock(self, obj):
        return obj.get_total_stock()

    def get_num_of_orders(self, obj):
        return obj.get_number_of_ordered_items_in_period()

    def get_compressed_product_picture_url(self, obj):
        return f"https://{settings.AWS_S3_COMPRESSED_IMAGES_DOMAIN}/{obj.product_picture_url.name}" if obj.product_picture_url else ""

    class Meta:
        model = Product
        fields = ("__all__")
        read_only_fields = ("total_stock", "num_of_orders",)


class SimpleProductSerializer(serializers.ModelSerializer):
    total_stock = serializers.SerializerMethodField()
    num_of_orders =serializers.SerializerMethodField()
    compressed_product_picture_url = serializers.SerializerMethodField( read_only=True )

    def get_total_stock(self, obj):
        return obj.get_total_stock()

    def get_num_of_orders(self, obj):
        return obj.get_number_of_ordered_items_in_period()

    def get_compressed_product_picture_url(self, obj):
        return f"https://{settings.AWS_S3_COMPRESSED_IMAGES_DOMAIN}/{obj.product_picture_url.name}" if obj.product_picture_url else ""

    class Meta:
        model = Product
        fields = ("__all__")
        read_only_fields = ("total_stock", "num_of_orders",)

class StockSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='product',
        queryset=Product.objects.all()
    )
    product = ProductSerializer( read_only=True )

    class Meta:
        model = ProductStock
        fields = (
            "product",
            "product_id",
            "quantity",
            "num_of_ordered_items",
            "num_of_remaining_items"
        )

class StoreProductSerializer(serializers.ModelSerializer):
    current_stock = ProductStockSerializer( read_only=True )
    stocks = ProductStockSerializer( read_only=True, many=True )
    total_stock = serializers.SerializerMethodField()
    num_of_orders =serializers.SerializerMethodField()
    compressed_product_picture_url = serializers.SerializerMethodField( read_only=True )

    def get_total_stock(self, obj):
        return obj.get_total_stock()

    def get_num_of_orders(self, obj):
        return obj.get_number_of_ordered_items_in_period()

    def get_compressed_product_picture_url(self, obj):
        return f"https://{settings.AWS_S3_COMPRESSED_IMAGES_DOMAIN}/{obj.product_picture_url.name}" if obj.product_picture_url else ""
    class Meta:
        model = Product
        fields = ("__all__")
        read_only_fields = ("total_stock", "num_of_orders")

class OrderItemSerializer(serializers.ModelSerializer):
    product = StoreProductSerializer( read_only=True )
    product_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='product',
        queryset=Product.objects.all()
    )
    order_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='order',
        queryset=Order.objects.all()
    )
    product_stock_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='product_stock',
        queryset=ProductStock.objects.all()
    )

    class Meta:
        model = OrderItem
        fields = ("__all__")
        read_only_fields = ('order', 'product_stock')

    def update(self, instance, validated_data):
        if validated_data.get( "quantity" ):
            product_stock = instance.product_stock.num_of_remaining_items + instance.quantity
            if validated_data.get("quantity") > product_stock:
                raise serializers.ValidationError("Order item quantity exceeds product quantity")
        item = super().update(instance, validated_data)
        return item

    def create(self, validated_data):
        if validated_data.get("quantity") > validated_data.get("product_stock").num_of_remaining_items:
            raise serializers.ValidationError("Order item quantity exceeds product quantity")
        item = super().create(validated_data)
        return item


class PaymentSerializer(serializers.ModelSerializer):
    order_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='order',
        queryset=Order.objects.all()
    )

    class Meta:
        model = Payment
        fields = ("__all__")
        read_only_fields = ( 'order', )

class OrderSerializer(serializers.ModelSerializer):
    store = SimpleStoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )
    customer = StoreCustomerSerializer( read_only=True )
    customer_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='customer',
        queryset=Customer.objects.all()
    )
    order_items = OrderItemSerializer( many=True, read_only=True )
    total_amount = serializers.FloatField( read_only=True )
    payments = PaymentSerializer( many=True, read_only=True )
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "store",
            "store_id",
            "customer",
            "customer_id",
            "delivery_fee",
            "total_amount",
            "order_items",
            "payments",
            "amount_paid",
            "balance",
            "payment_status",
            "confirmed",
            "profit",
            "paid_on",
            "number",
            "created_at"
        )
        read_only_fields = ( 'created_at', "payment_status" )

    def get_payment_status(self, obj):
        return obj.get_payment_status_display()

class StoreOrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer( read_only=True )
    customer_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='customer',
        queryset=Customer.objects.all()
    )
    order_items = OrderItemSerializer( many=True, read_only=True )
    order_items_ids = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='order_items',
        queryset=OrderItem.objects.all()
    )
    payments = PaymentSerializer( many=True, read_only=True )
    number_of_products = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    def get_number_of_products(self, obj):
        return obj.get_number_of_products()

    def get_payment_status(self, obj):
        return obj.get_payment_status_display()

    class Meta:
        model = Order
        fields = (
            "id",
            "store",
            "customer",
            "customer_id",
            "delivery_fee",
            "total_amount",
            "order_items",
            "order_items_ids",
            "payments",
            "amount_paid",
            "balance",
            "payment_status",
            "profit",
            "confirmed",
            "number_of_products",
            "paid_on",
            "number",
            "created_at"
        )
        read_only_fields = (
            "number_of_products", "payment_status"
        )


class CustomerOrderSerializer(serializers.ModelSerializer):
    store = StoreSerializer( read_only=True )
    store_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='store',
        queryset=Store.objects.all()
    )
    order_items = OrderItemSerializer( many=True, read_only=True )
    order_items_ids = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source='order_items',
        queryset=OrderItem.objects.all()
    )
    number_of_products = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    def get_number_of_products(self, obj):
        return obj.get_number_of_products()

    def get_payment_status(self, obj):
        return obj.get_payment_status_display()

    class Meta:
        model = Order
        fields = (
            "id",
            "store",
            "store_id",
            "delivery_fee",
            "total_amount",
            "order_items",
            "order_items_ids",
            "payments",
            "amount_paid",
            "balance",
            "payment_status",
            "profit",
            "confirmed",
            "number_of_products",
            "paid_on",
            "number",
            "created_at"
        )
        read_only_fields = (
            "number_of_products", "payment_status"
        )
