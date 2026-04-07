from django.contrib import admin
from .models import Product, orders, Customers
admin.site.register(Product)
admin.site.register(Customers)
admin.site.register(orders)

