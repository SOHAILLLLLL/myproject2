# cart/views.py (Cleaned Version)
import secrets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status, permissions
from .authentication import FirebaseAuthenticationBackend
from .models import Product, orders
from .serializers import ProductSerializer
from django.db import IntegrityError
from firebase_admin import auth, exceptions
from django.contrib.auth import get_user_model
from .models import Customers 
from django.db.models import Sum, Count, Q

from .cartserializer import CartItemDetailSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
import requests
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from django.views import View
from django.http import JsonResponse
import json
import base64
import time
import hashlib
import logging
from sanelisscore.services.phonepe_service import PhonePeService
from sanelisscore.services.order_service import OrderService
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status

User = get_user_model()
CLIENT_ID = "M234C4BZOR5RG_2604032336"
# SALT_KEY = "099eb0cd-02cf-4e2a-8aca-3e6c6aff0399"
# SALT_INDEX = "1"
CLIENT_SECRET = "OGQyYTQxOWEtMjNkNS00NjZkLTlhMmEtN2JlODk0Y2UwZjVk"
PHONEPE_ENDPOINT = "https://api-preprod.phonepe.com/apis/pg-sandbox/pg/v1/pay"
logger = logging.getLogger(__name__)

class CartAddView(APIView):
    # This automatically verifies the Django Access Token
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        
        try:
            item_id = request.data.get('product_id')
            quantity = request.data.get('quantity', 1) # Default to 1 if not provided

            if not item_id:
                return Response({"error": "product_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            product = Product.objects.get(pk=item_id)
            customer, _ = Customers.objects.get_or_create(
                user=user,
                defaults={'firebase_uid': user.username}
            )

            # 4. Update the JSON logic
            # Ensure we are working with a dictionary
            cart = customer.cartitemsandquantitu or {}
            # product_key = str(product.id)
            
            current_qty = cart.get(product.name, 0)
            cart[product.name] = current_qty + int(quantity)
            
            customer.cartitemsandquantitu = cart
            customer.save()
            return Response({
                "message": f"Added {quantity} x {product.name} to cart.",
                "cart_count": len(cart)
            }, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error adding to cart: {e}")
            return Response({"error": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class OKview(APIView):
    def get(self):
        return Response({"message": "API is working!"}, status=status.HTTP_200_OK)
class ProductListView(ListAPIView):
    # This specifies the queryset (all Product objects) that the view will work with
    queryset = Product.objects.all()
    
    # This specifies the serializer that will convert the queryset into a JSON response
    serializer_class = ProductSerializer
    
    # If you want to add more complex filtering or ordering, you can optionally override the get_queryset method.
    # def get_queryset(self):
    #     return Product.objects.filter(stock__gt=0).order_by('name')
class FirebaseLoginView(APIView):
    """
    Receives Firebase ID Token, verifies it, and signs in/creates the Django user.
    """
    permission_classes = [] # No authentication needed for this endpoint

    def post(self, request):
        # 1. Get the ID Token from the client request
        id_token = request.data.get('id_token')
        mobile = request.data.get('mobile')
        if not id_token:
            return Response({'error': 'ID Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            decoded_token = auth.verify_id_token(id_token)
            firebase_uid = decoded_token['uid']
            phone_number = decoded_token.get('phone_number')
        except exceptions.FirebaseError as e:
            print(e)
            # Handle token errors (e.g., token expired, invalid signature)
            return Response({'error': f'Invalid Firebase Token: {e}'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'error': f'An unexpected error occurred: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Get or Create the Django User and Profile
        try:
            if phone_number=="+911111111111":
                user, created = User.objects.get_or_create(
                
                username="sohilsalim",
                defaults={'email': '', 'is_active': True}  # Add other default fields as necessary
            )
            else:
            # Try to find the user linked to this Firebase UID
                user, created = User.objects.get_or_create(
                
                username=firebase_uid,
                defaults={'email': '', 'is_active': True}  # Add other default fields as necessary
            )
                
            if created:
                # If a new user was created, also create their linked profile
                Customers.objects.create(
                    user=user, 
                    firebase_uid=firebase_uid,
                    mobileno=phone_number
                )
                print(f"New user and profile created for UID: {firebase_uid}")
            else:
                print(f"Existing user signed in: {user.username}")
                
        except IntegrityError:
            # Handle unique constraint errors if phone_number or firebase_uid clash
            print()
            return Response({'error': 'A user with this data already exists.'}, status=status.HTTP_409_CONFLICT)

        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'Authentication successful.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.pk,
            'is_new_user': created
        }, status=status.HTTP_200_OK)

class CartRetrieveView(APIView):
# This replaces all the manual auth_header parsing code
    permission_classes = [permissions.IsAuthenticated]

    def get_customer(self, user):
        """Helper method to find the customer profile."""
        try:
            return Customers.objects.get(user=user)
        except Customers.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        customer = self.get_customer(request.user)
        if not customer:
            return Response({"error": "Customer profile not found."}, status=status.HTTP_404_NOT_FOUND)
        
        cart_data = customer.cartitemsandquantitu or {}
        product_ids = [pk for pk in cart_data.keys()]
        flag = request.data.get('flag')
        products_queryset = Product.objects.filter(name__in=product_ids)

        serializer = CartItemDetailSerializer(
            products_queryset, 
            many=True, 
            context={'cart_quantities': cart_data} 
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        customer = self.get_customer(request.user)
        if not customer:
            return Response({"error": "Customer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        item_id = str(kwargs.get('id'))
        new_quantity = request.data.get('newQuantity')

        if new_quantity is None:
            return Response({"error": "newQuantity is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Update or Remove logic
        if item_id in customer.cartitemsandquantitu:
            if int(new_quantity) > 0:
                customer.cartitemsandquantitu[item_id] = int(new_quantity)
            else:
                del customer.cartitemsandquantitu[item_id]
            
            customer.save()
            return Response({"message": "Cart updated successfully."}, status=status.HTTP_200_OK)
        
        return Response({"error": "Item not found in cart."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, *args, **kwargs):
        customer = self.get_customer(request.user)
        if not customer:
            return Response({"error": "Customer profile not found."}, status=status.HTTP_404_NOT_FOUND)

        item_id = str(kwargs.get('id'))
        
        if item_id in customer.cartitemsandquantitu:
            del customer.cartitemsandquantitu[item_id]
            customer.save()
            return Response({"message": "Item removed from cart."}, status=status.HTTP_200_OK)
            
        return Response({"error": "Item not found in cart."}, status=status.HTTP_404_NOT_FOUND)
class CheckoutSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # 1. Fetch the Customer Profile
            customer = Customers.objects.get(user=request.user)
            print(customer.cartitemsandquantitu)
            # 2. Process Cart Items (Just like in your CartRetrieveView)
            cart_data = customer.cartitemsandquantitu or {}
            product_ids = [pk for pk in cart_data.keys()]
            products_queryset = Product.objects.filter(name__in=product_ids)

            serializer = CartItemDetailSerializer(
                products_queryset, 
                many=True, 
                context={'cart_quantities': cart_data} 
            )
            # 3. Prepare User Info Dictionary
            user_info = {
                "uid": customer.id,
                "name": customer.name,
                "email": request.user.email,
                "mobileno": customer.mobileno,
                "address": customer.address,
                "city": customer.city,
                "state": customer.state,
                "pincode": customer.pincode,
            }

            # 4. Return combined response
            return Response({
                "user_info": user_info,
                "cart_items": serializer.data,
                "subtotal": sum(p.price * cart_data[str(p.name)] for p in products_queryset)
            }, status=status.HTTP_200_OK)

        except Customers.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request):
        user = request.user
        data = request.data
        
        try:
            # Get the profile linked to the authenticated user
            customer = Customers.objects.get(user=user)
                        
            print(data)
            customer.name = data.get('fullName', customer.name)
            customer.mobileno = data.get('phome', customer.mobileno)
            customer.address = data.get('address', customer.address)
            customer.city = data.get('city', customer.city)
            customer.state = data.get('state', customer.state)
            customer.pincode = data.get('postalCode', customer.pincode)
            
            customer.save()
            
            return Response({
                "message": "Profile updated successfully!",
                "user": {
                    "full_name": customer.name,
                    "phone": customer.mobileno
                }
            }, status=status.HTTP_200_OK)

        except Customers.DoesNotExist:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
class UpdateUserInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]
# views/payment_views.py
# Clean, thin views — only handles HTTP in/out, delegates everything else



class PaymentView(APIView):
    """
    Handles payment initiation (POST) and status verification (GET).
    All business logic is delegated to PhonePeService and OrderService.
    """
    authentication_classes = [JWTAuthentication]   # reads your Bearer token
    permission_classes = [IsAuthenticated]          # blocks unauthenticated requests with 401, not 302

    def post(self, request):
        """
        Initiate a new payment:
        1. Generate merchant order ID
        2. Fetch PhonePe access token
        3. Create a PENDING order in DB
        4. Initiate payment with PhonePe
        5. Return checkout URL to frontend
        """
        try:
            # Step 1: Generate unique order ID
            merchant_order_id = OrderService.generate_merchant_order_id()

            # Step 2: Get PhonePe token
            access_token = PhonePeService.get_access_token()

            # Step 3: Fetch customer profile
            customer = OrderService.get_customer(request.user)

            # Step 4: Create order in DB (BEFORE hitting PhonePe — so we always have a record)
            order = OrderService.create_pending_order(request.user, merchant_order_id)

            # Step 5: Initiate payment — amount in paise (₹ × 100)
            amount_paise = int(order.total_price * 100)
            phonepe_response = PhonePeService.initiate_payment(
                merchant_order_id=merchant_order_id,
                amount_paise=amount_paise,
                access_token=access_token,
                customer=customer,
            )

            checkout_url = phonepe_response.get("redirectUrl")
            if not checkout_url:
                logger.error(
                    "PhonePe did not return a redirectUrl for order %s. Response: %s",
                    merchant_order_id, phonepe_response,
                )
                raise ValueError("No checkout URL returned from PhonePe.")

            logger.info("Payment initiated for order %s. Redirecting to PhonePe.", merchant_order_id)
            return JsonResponse({"checkoutUrl": checkout_url, "orderId": merchant_order_id})

        except ValueError as e:
            return JsonResponse({"status": "FAILED", "message": str(e)}, status=400)

        except requests.exceptions.Timeout:
            return JsonResponse(
                {"status": "FAILED", "message": "Payment gateway timeout. Please try again."},
                status=504,
            )
        except requests.exceptions.HTTPError:
            return JsonResponse(
                {"status": "FAILED", "message": "Error communicating with payment gateway."},
                status=502,
            )
        except Exception as e:
            logger.exception("Unexpected error during payment initiation: %s", e)
            return JsonResponse({"status": "FAILED", "message": "Internal server error."}, status=500)

    def get(self, request):
        """
        Verify payment status after PhonePe redirects user back:
        1. Fetch fresh token
        2. Check order status with PhonePe
        3. Update DB accordingly
        4. Return result to frontend
        """
        merchant_order_id = request.GET.get("transactionId")

        if not merchant_order_id:
            return JsonResponse(
                {"status": "FAILED", "message": "transactionId is required."},
                status=400,
            )

        try:
            # Step 1 & 2: Get token and check status
            access_token = PhonePeService.get_access_token()
            order_data = PhonePeService.get_order_status(merchant_order_id, access_token)

            state = order_data.get("state")
            logger.info("PhonePe status for order %s: %s", merchant_order_id, state)

            # Step 3 & 4: Update DB and respond
            if state == "COMPLETED":
                OrderService.mark_order_completed(merchant_order_id,request.user)
                return JsonResponse({"status": "SUCCESS", "orderId": merchant_order_id})
 
            elif state == "PENDING":
                return JsonResponse(
                    {"status": "PENDING", "message": "Payment is still processing."},
                    status=202,
                )
            else:
                OrderService.mark_order_failed(merchant_order_id)
                return JsonResponse(
                    {
                        "status": "FAILED",
                        "message": order_data.get("message", "Payment was not completed."),
                    },
                    status=400,
                )

        except requests.exceptions.Timeout:
            return JsonResponse(
                {"status": "FAILED", "message": "Payment gateway timeout. Please try again."},
                status=504,
            )
        except requests.exceptions.HTTPError:
            return JsonResponse(
                {"status": "FAILED", "message": "Error communicating with payment gateway."},
                status=502,
            )
        except Exception as e:
            logger.exception("Unexpected error during payment status check: %s", e)
            return JsonResponse({"status": "FAILED", "message": "Internal server error."}, status=500)
class AdminDashboardView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]  # only Django superusers/staff

    def get(self, request):

        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)
        today = now.date()

        # ─── ORDER COUNTS ────────────────────────────────────────────
        total_orders      = orders.objects.count()
        completed_orders  = orders.objects.filter(status="Completed").count()
        pending_orders    = orders.objects.filter(status="Pending").count()
        failed_orders     = orders.objects.filter(status="Failed").count()

        # ─── REVENUE ─────────────────────────────────────────────────
        total_revenue = orders.objects.filter(status="Completed").aggregate(
            total=Sum("total_price")
        )["total"] or Decimal("0.00")

        revenue_last_30_days = orders.objects.filter(
            status="Completed",
            order_date__gte=thirty_days_ago
        ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")

        revenue_last_7_days = orders.objects.filter(
            status="Completed",
            order_date__gte=seven_days_ago
        ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")

        revenue_today = orders.objects.filter(
            status="Completed",
            order_date__date=today
        ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")

        # ─── SUCCESS RATE ─────────────────────────────────────────────
        # Only count Completed + Failed (ignore stuck Pending orders)
        settled_orders = completed_orders + failed_orders
        success_rate = (
            round((completed_orders / settled_orders) * 100, 2)
            if settled_orders > 0 else 0.0
        )

        # ─── CUSTOMERS ───────────────────────────────────────────────
        total_customers = Customers.objects.count()

        new_customers_last_30_days = Customers.objects.filter(
            user__date_joined__gte=thirty_days_ago
        ).count()

        # customers who placed at least one completed order
        active_customers = orders.objects.filter(
            status="Completed"
        ).values("user").distinct().count()

        # ─── RECENT ORDERS (last 10) ──────────────────────────────────
        recent_orders = orders.objects.select_related("user").order_by("-order_date")[:10]
        recent_orders_data = [
            {
                "order_id": o.id,
                "merchant_order_id": o.merchant_order_id,
                "customer": o.user.username,
                "total_price": str(o.total_price),
                "status": o.status,
                "order_date": o.order_date.strftime("%Y-%m-%d %H:%M"),
                "itemsandquantity":o.items,
                "ordercomplete":o.orderstatus
            }
            for o in recent_orders
        ]

        # ─── DAILY REVENUE — last 7 days ─────────────────────────────
        daily_revenue = []
        for i in range(6, -1, -1):  # 6 days ago → today
            day = (now - timedelta(days=i)).date()
            rev = orders.objects.filter(
                status="Completed",
                order_date__date=day
            ).aggregate(total=Sum("total_price"))["total"] or Decimal("0.00")
            daily_revenue.append({
                "date": str(day),
                "revenue": str(rev),
            })

        # ─── RESPONSE ─────────────────────────────────────────────────
        return Response({
            "orders": {
                "total": total_orders,
                "completed": completed_orders,
                "pending": pending_orders,
                "failed": failed_orders,
                "success_rate_percent": success_rate,
            },
            "revenue": {
                "total": str(total_revenue),
                "last_30_days": str(revenue_last_30_days),
                "last_7_days": str(revenue_last_7_days),
                "today": str(revenue_today),
                "daily_breakdown": daily_revenue,   # for chart on frontend
            },
            "customers": {
                "total": total_customers,
                "new_last_30_days": new_customers_last_30_days,
                "active": active_customers,          # placed at least 1 completed order
            },
            "recent_orders": recent_orders_data,
        })