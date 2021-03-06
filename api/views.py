from urllib.parse import urljoin

from django_rest_passwordreset.views import (
    ResetPasswordConfirm,
)
from django_rest_passwordreset.models import (
    ResetPasswordToken,
)
from django_rest_passwordreset.signals import (
    pre_password_reset,
    post_password_reset
)

from django_filters.rest_framework import DjangoFilterBackend

from django.http.response import HttpResponseRedirect
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings
from django.contrib.auth.password_validation import validate_password, get_password_validators

from rest_framework import generics
from rest_framework.generics import get_object_or_404
from rest_framework import status, exceptions
from rest_framework import filters
from rest_framework.views import APIView, Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.authtoken.models import Token
from rest_framework.parsers import FileUploadParser, JSONParser, MultiPartParser
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny

from main.tasks import (
    send_email_async,
)
from .serializers import (
    UserSerializer,
    AuthTokenSerializer,
    VerificationCodeSerializer,
    ChangePasswordSerializer,
    StoreSerializer,
    AdminSerializer,
    CustomerSerializer,
    StoreCustomerSerializer,
    ProductSerializer,
    StoreProductSerializer,
    OrderSerializer,
    OrderItemSerializer,
    StoreOrderSerializer,
    CustomerOrderSerializer,
    ProductStockSerializer,
    StockSerializer,
    PaymentSerializer,
    ProductCustomerSerializer,
    CategorySerializer
)
from main.models import (
    VerificationCode,
    Store,
    Admin,
    Customer,
    Product,
    Order,
    OrderItem,
    ProductStock,
    Payment,
    Category
)

User = get_user_model()

class UsersEndpoint(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"user": serializer.data, "token": token.key},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        user = serializer.save()
        verification_code = VerificationCode.objects.create(email=user.email)
        confirm_email_url = f"users/verify/?code={verification_code.code}"
        send_email_async.delay(
            template_id=settings.TEMPLATE_EMAIL_WITH_URL_ID,
            tos=[user.email],
            subject='Souko - Account Confirmation Email',
            context={
                'subject': 'Souko - Account Confirmation Email',
                'first_name': user.first_name,
                'message': '''We are so happy to have you as a user on our platform, kindly click on the url below to confirm your account''',
                'url': f"{settings.EMAIL_BASE_URL}{confirm_email_url}"
            },
            index=0
        )
        return user

class UserEndpoint( generics.RetrieveUpdateAPIView ):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    permission_classes = ( IsAuthenticated, )

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

class CustomAuthToken(ObtainAuthToken):
    serializer_class = AuthTokenSerializer
    permission_classes = ( AllowAny, )

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})

class UserVerify(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        try:
            code = request.query_params.get("code", None)
            verification_code = VerificationCode.objects.get( code=code )

            user = get_object_or_404(User, email=verification_code.email)
            if not user.is_email_confirmed:
                user.is_email_confirmed = True
                user.save(update_fields=["is_email_confirmed"])
            verification_code.delete()
            return HttpResponseRedirect( redirect_to=f"{settings.FRONTEND_BASE_URL}{'account/auth/sign-in'}" )
        except VerificationCode.DoesNotExist:
            return HttpResponseRedirect( redirect_to=f"{settings.FRONTEND_BASE_URL}{'account/auth/sign-in'}" )

class ChangePasswordEndpoint(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = ( IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.get(pk=self.request.user.id)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if authenticate(email=user.email, password=old_password):
            user.set_password(new_password)
            user.save(update_fields=["password"])
            return Response({"message": "Password Changed Successfully"})
        else:
            return Response(
                {"message": "Old password does not match password on file"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CategoriesEndpoint( generics.ListCreateAPIView ):
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    permission_classes = ( IsAuthenticated, )

class StoresEndpoint(generics.ListCreateAPIView):
    serializer_class = StoreSerializer
    queryset = Store.objects.all()
    permission_classes = ( IsAuthenticated, )

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            user_id = data.pop( 'user_id' )
            admin = Admin.objects.create( **{
                'role':'OWNER',
                'user_id':user_id
            } )
            
            data['admins_ids'] = [admin.pk]
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            user = User.objects.get(pk=user_id)
            user.is_onboarded = True
            user.save(update_fields=["is_onboarded"])

            store = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers,
            )
        except Exception as e:
            return Response(
                { "error": str(e) },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StoreEndpoint(generics.RetrieveUpdateAPIView):
    serializer_class = StoreSerializer
    queryset = Store.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class StoreAdminsEndpoint(generics.ListAPIView):
    serializer_class = AdminSerializer
    permission_classes = ( IsAuthenticated, )

    def get_queryset(self):
        store = get_object_or_404(Store.objects.filter( pk=self.kwargs["pk"] ))
        return store.admins.all()


class StoreProfitReportEndpoint(generics.GenericAPIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    schema = None

    def get(self, request, *args, **kwargs):
        try:
            store = get_object_or_404(Store, pk=self.kwargs["pk"])
            period = int(request.query_params.get("period", 3))
            profit_per_period = store.get_profit_by_period(period=period)
            profit_report_per_period = store.get_profit_report_by_period(period=period)
            return Response({ "profit": profit_per_period, "profit_report": profit_report_per_period })
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreOrdersReportEndpoint(generics.GenericAPIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    schema = None

    def get(self, request, *args, **kwargs):
        try:
            store = get_object_or_404(Store, pk=self.kwargs["pk"])
            period = int(request.query_params.get("period", 3))

            orders_records_report = store.get_orders_report_by_period(period=period)
            number_of_orders = store.get_num_of_orders_report_by_period(period=period)
            return Response({ 'orders_record': orders_records_report, 'number_of_orders': number_of_orders })
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreProductStocksReportEndpoint(generics.GenericAPIView):
    permission_classes = ( IsAuthenticated, )
    serializer_class = ProductSerializer
    schema = None

    def get(self, request, pk, *args, **kwargs):
        try:
            store = get_object_or_404( Store, pk=pk )

            low_products_report = store.get_low_products_stock()
            low_products_serializer = ProductSerializer( low_products_report, many=True )

            period = int(request.query_params.get("period", 3))
            best_selling_report = store.get_best_selling_product_by_period( period=period )
            best_selling_serializer = ProductSerializer( best_selling_report )
            return Response({'low_products':low_products_serializer.data, 'best_selling_products':best_selling_serializer.data if best_selling_report else None})
        except Exception as e:
            return Response( {"message": str(e)}, status=status.HTTP_400_BAD_REQUEST )


class StoreCustomersEndpoint(generics.ListAPIView):
    serializer_class = StoreCustomerSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering = ["-created_at"]
    ordering_fields = [ "created_at", ]
    search_fields = [
        "first_name",
        "last_name"
    ]

    def get_queryset(self):
        store = get_object_or_404(Store.objects.filter( pk=self.kwargs["pk"] ))
        return store.customers.all()

class StoreProductsEndpoint(generics.ListAPIView):
    serializer_class = StoreProductSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    ordering = ["-created_at"]
    ordering_fields = [ "created_at", ]
    search_fields = [
        "name"
    ]

    def get_queryset(self):
        store = get_object_or_404(Store.objects.filter( pk=self.kwargs["pk"] ))
        return store.products.all()


class StoreOrdersEndpoint(generics.ListAPIView):
    serializer_class = StoreOrderSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    ordering_fields = ["created_at", "payment_status"]
    ordering = ["-created_at"]
    search_fields = [
        "customer__first_name",
        "customer__last_name"
    ]
    filterset_fields = ["payment_status",]

    def get_queryset(self):
        store = get_object_or_404(Store.objects.filter( pk=self.kwargs["pk"] ))
        return store.orders.all()


class CustomersEndpoint(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = ( IsAuthenticated, )


class CustomerEndpoint(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class CustomerOrdersEndpoint(generics.ListAPIView):
    serializer_class = CustomerOrderSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    ordering = ["-created_at"]
    ordering_fields = [ "created_at", ]
    search_fields = [
        "customer__first_name",
        "customer__last_name"
    ]
    filterset_fields = ["payment_status",]

    def get_queryset(self):
        customer = get_object_or_404(Customer.objects.filter( pk=self.kwargs["pk"] ))
        return customer.orders.all()


class CustomerOrderedProductsEndpoint(generics.ListAPIView):
    serializer_class = StoreProductSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter
    ]
    ordering = ["-created_at"]
    ordering_fields = [ "created_at", ]
    search_fields = [
        "name",
    ]

    def get_queryset(self):
        customer = get_object_or_404(Customer.objects.filter( pk=self.kwargs["pk"] ))
        return customer.get_ordered_products()


class ProductsEndpoint(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    permission_classes = ( IsAuthenticated, )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        stock_quantity = data.pop( 'quantity' )
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        product = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        stock = ProductStock.objects.create(**{
            'product_id': serializer.data['id'],
            'quantity': stock_quantity
        })

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class ProductEndpoint(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class ProductProductStocksEndpoint(generics.ListAPIView):
    serializer_class = ProductStockSerializer
    permission_classes = ( IsAuthenticated, )

    def get_queryset(self):
        product = get_object_or_404(Product.objects.filter( pk=self.kwargs["pk"] ))
        return product.stocks.all()


class ProductCustomersEndpoint(generics.ListAPIView):
    serializer_class = ProductCustomerSerializer
    permission_classes = ( IsAuthenticated, )
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    ordering = ["-created_at"]
    ordering_fields = [ "created_at", ]
    search_fields = [
        "first_name",
        "last_name",
        "city"
    ]

    def get_queryset(self):
        return Customer.objects.filter( orders__order_items__product__pk=self.kwargs["pk"] ).distinct()


class ProductStocksEndpoint(generics.ListCreateAPIView):
    serializer_class = ProductStockSerializer
    queryset = ProductStock.objects.all()
    permission_classes = ( IsAuthenticated, )


class ProductStockEndpoint(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = StockSerializer
    queryset = ProductStock.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class OrdersEndpoint(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = ( IsAuthenticated, )


class OrderEndpoint(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class OrderOrderItemsEndpoint(generics.ListAPIView):
    serializer_class = OrderItemSerializer
    permission_classes = ( IsAuthenticated, )

    def get_queryset(self):
        order = get_object_or_404(Order.objects.filter( pk=self.kwargs["pk"] ))
        return order.order_items.all()


class OrderPaymentsEndpoint(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = ( IsAuthenticated, )

    def get_queryset(self):
        order = get_object_or_404(Order.objects.filter( pk=self.kwargs["pk"] ))
        return order.payments.all()


class OrderItemsEndpoint(generics.CreateAPIView):
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()
    permission_classes = ( IsAuthenticated, )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        product = Product.objects.get( pk=data.get("product_id") )
        data['product_stock_id'] = product.current_stock.pk
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class OrderItemEndpoint(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = OrderItemSerializer
    queryset = OrderItem.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)


class PaymentsEndpoint(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    permission_classes = ( IsAuthenticated, )


class PaymentEndpoint(generics.RetrieveUpdateAPIView):
    serializer_class = PaymentSerializer
    queryset = Payment.objects.all()
    permission_classes = ( IsAuthenticated, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
