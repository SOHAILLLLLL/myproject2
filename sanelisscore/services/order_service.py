# services/order_service.py
# Handles all order-related business logic and DB operations

import secrets
import time
import logging
from decimal import Decimal
from django.db import transaction
from sanelisscore.models import orders, Customers,Product  # adjust import path

logger = logging.getLogger(__name__)


class OrderService:
    """
    Handles all order creation, updates, and business logic.
    Keeps DB operations separate from views and payment logic.
    """

    @staticmethod
    def generate_merchant_order_id() -> str:
        """
        Generate a unique, traceable merchant order ID.
        Format: ORD-{timestamp}-{random_hex}
        Example: ORD-1712345678-A3F9C1
        """
        timestamp = int(time.time())
        random_suffix = secrets.token_hex(3).upper()
        return f"ORD-{timestamp}-{random_suffix}"

    @staticmethod
    def get_customer(user) -> "Customers":
        """Fetch the customer profile for a given user."""
        try:
            return Customers.objects.get(user=user)
        except Customers.DoesNotExist:
            logger.error("Customer profile not found for user: %s", user.id)
            raise

    @staticmethod
    def calculate_cart_total(cart_items: dict) -> Decimal:
        """
        Calculate the total from the customer's cart.
        cart_items format: { "product_id": { "price": 99.99, "quantity": 2 }, ... }
        Adjust field names to match your actual cart structure.
        """
        product_ids = [pk for pk in cart_items.keys()]
        products_queryset = Product.objects.filter(name__in=product_ids)
        return sum(p.price * cart_items[str(p.name)] for p in products_queryset)

        # total = Decimal("0.00")
        # for item in cart_items.values():
        #     price = Decimal(str(item.get("price", 0)))
        #     quantity = int(item.get("quantity", 1))
        #     total += price * quantity
        # return total

    @staticmethod
    @transaction.atomic
    def create_pending_order(user, merchant_order_id: str) -> "orders":
        """
        Create an order in PENDING state before initiating payment.
        Uses atomic transaction — if anything fails, DB is not changed.
        """
        customer = OrderService.get_customer(user)
        cart_items = customer.cartitemsandquantitu or {}

        if not cart_items:
            raise ValueError("Cart is empty. Cannot create an order.")

        total_price = OrderService.calculate_cart_total(cart_items)

        new_order = orders.objects.create(
            user=user,
            items=list(cart_items.values()),   # snapshot cart at time of purchase
            total_price=total_price,
            merchant_order_id=merchant_order_id,
            status="Pending",
        )

        logger.info(
            "Created pending order %s for user %s (total: ₹%s)",
            merchant_order_id, user.id, total_price,
        )
        return new_order

    @staticmethod
    @transaction.atomic
    def mark_order_completed(merchant_order_id: str,user) -> "orders":
        """Mark an order as COMPLETED after successful payment confirmation."""
        try:
            order = orders.objects.select_for_update().get(
                merchant_order_id=merchant_order_id
            )
        except orders.DoesNotExist:
            logger.error("Order not found for merchant_order_id: %s", merchant_order_id)
            raise

        if order.status == "Completed":
            logger.warning("Order %s already marked completed. Skipping.", merchant_order_id)
            return order

        order.status = "Completed"
        order.save(update_fields=["status"])
        Customers.objects.filter(user=user).update(cartitemsandquantitu={})

        # TODO: Reduce inventory for items in order.items
        # InventoryService.deduct_stock(order.items)

        logger.info("Order %s marked as Completed.", merchant_order_id)
        return order

    @staticmethod
    @transaction.atomic
    def mark_order_failed(merchant_order_id: str) -> "orders":
        """Mark an order as FAILED."""
        try:
            order = orders.objects.select_for_update().get(
                merchant_order_id=merchant_order_id
            )
        except orders.DoesNotExist:
            logger.error("Order not found for merchant_order_id: %s", merchant_order_id)
            raise

        order.status = "Failed"
        order.save(update_fields=["status"])
        logger.info("Order %s marked as Failed.", merchant_order_id)
        return order