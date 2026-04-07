# models.py
from django.db import models
from django.contrib.auth.models import User # Or your Custom User Model

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    isCombo = models.BooleanField(default=False)
    size = models.CharField(max_length=50, null=True, blank=True)
    photos = models.JSONField(default=list, blank=True)
    ingredients = models.JSONField(default=list, blank=True)
    rating = models.FloatField(default=0)
    reviews = models.IntegerField(default=0)
    stock = models.IntegerField(default=10)
    def __str__(self):
        return self.name
    # ... other fields
class orders(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.JSONField(default=dict, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    order_date = models.DateTimeField(auto_now_add=True)
    merchant_order_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    orderstatus = models.CharField(max_length=50, default='Pending')
    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
class Customers(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True, blank=True)  
    firebase_uid = models.CharField(max_length=255, unique=True)
    mobileno = models.CharField(max_length=15, null=True,blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    state = models.CharField(max_length=20,null=True,blank=True)
    cartitemsandquantitu = models.JSONField(default=dict, blank=True)
    # def __str__(self):
    #     return f"Profile of {self.user.username}"
    #     if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
    #     if (!formData.phone.trim()) newErrors.phone = 'Phone number is required';
    #     if (!formData.address.trim()) newErrors.address = 'Street address is required';
    #     if (!formData.city.trim()) newErrors.city = 'City is required';
    #     if (!formData.state.trim()) newErrors.state = 'State is required';
    #     if (!formData.postalCode.trim()) newErrors.postalCode = 'Postal code is required';
