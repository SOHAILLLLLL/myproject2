# cart/serializers.py (Ensure these imports and classes are present)
from rest_framework import serializers
from .models import Customers, Product # Assuming you have a Product model imported here

# --- Existing Product Serializer (if needed for the product list view) ---
# class ProductSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Product
#         fields = '__all__'

# --- New Serializer for the Cart Item ---

class CartItemDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for returning full product details plus the quantity in the cart.
    """
    # This field will be calculated dynamically and added to the product details
    quantity = serializers.SerializerMethodField() 
    
    class Meta:
        model = Product
        # Include fields you want the client to see (e.g., name, price, image)
        fields = ('id', 'name', 'price', 'photos', 'quantity') 
        # Note: Replace 'name', 'price', and 'image' with your actual Product model fields
    def get_quantity(self, obj):
            product_id = obj.name
            cart_quantities = self.context.get('cart_quantities', {})
            return cart_quantities.get(str(product_id), 0)
# --- Cart Serializer (optional, if needed for a different structure) ---
# ... (your other serializers)