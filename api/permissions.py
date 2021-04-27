from rest_framework import permissions

class ProductsLimitPermission(permissions.BasePermission):
    """
    Global permission check for products limit
    """

    def has_permission(self, request, view):
        if request.method in [ 'POST' ]:
            hit_products_limit = request.user.admin.store.my_subscription.hit_products_limit()
            return not hit_products_limit
        return True
