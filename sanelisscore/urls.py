# store/urls.py

from django.urls import path
from .views import CartAddView,ProductListView,FirebaseLoginView,CartRetrieveView, CheckoutSummaryView,OKview,PaymentView, AdminDashboardView
from rest_framework_simplejwt.views import TokenRefreshView
urlpatterns = [
path('',OKview.as_view(),name='okay'),
    path('cart/add/', CartAddView.as_view(), name='add_to_cart'),
    path('cart/retrieve/', CartRetrieveView.as_view(), name='cart_retrieve'),
    path('cart/update-quantity/<str:id>/', CartRetrieveView.as_view(), name='cart_update_quantity'),
    path('cart/delete/<str:id>/', CartRetrieveView.as_view(), name='cart_delete_item'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('auth/verify_firebase_token/', FirebaseLoginView.as_view(), name='firebase_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('checkout/',CheckoutSummaryView.as_view(),name='checkout'),
    path('payment/initiate/', PaymentView.as_view(), name='initiate_payment'),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
]