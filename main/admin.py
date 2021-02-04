from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin
from .models import *

models = [
    VerificationCode,
    Category,
    Store,
    Product,
    ProductStock,
    Admin,
    Customer,
    Order,
    OrdersTimestampedMetric,
    ProfitTimestampedMetric,
    StorePeriodicTask,
    OrderItem,
    Payment
]

class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "is_staff")

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserAdmin(UserAdmin):

    add_form = UserCreationForm
    list_display = ("email", "full_name", "is_email_confirmed", "is_onboarded", "created_at")
    search_fields = ("email", "first_name", "last_name")
    list_filter = (
        "is_email_confirmed",
        "is_staff",
        "is_superuser",
        "is_active",
        "is_onboarded"
    )
    ordering = ("email",)

    def get_queryset(self, request):
        qs = super(UserAdmin, self).get_queryset(request)
        return qs

    fieldsets = (
        (
            "Personal info",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "dob"
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_onboarded",
                    "is_email_confirmed",
                    "is_superuser",
                    "is_staff",
                    "is_active",
                    "created_at",
                    "required_change_password",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                #'classes': ('wide',),
                "fields": ("email", "first_name", "last_name", "password1", "password2")
            },
        ),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".title()

    readonly_fields = ("password", "created_at")


for model in models:
    admin.site.register(model)


admin.site.register(User, UserAdmin)

# Register your models here.
