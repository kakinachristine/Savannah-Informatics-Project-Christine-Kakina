from django.db import models
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from africastalking.SMS import SMSService
from django.conf import settings
import requests
import logging
from django.conf import settings
from rest_framework.exceptions import ValidationError




from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


from .models import Customer, Category, Product, Order
from .serializers import CustomerSerializer, CategorySerializer, ProductSerializer, OrderSerializer



logger = logging.getLogger(__name__)
sms = SMSService(settings.AT_USERNAME, settings.AT_API_KEY)



# CREATE NEW CUSTOMER
class CustomerCreateView(generics.CreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        phone = serializer.validated_data.get("phone")

        # Check if phone already exists
        if Customer.objects.filter(phone=phone).exists():
            logger.warning("Attempt to create duplicate customer with phone: %s", phone)
            raise ValidationError({"phone": "A customer with this phone number already exists."})

        # Save new customer
        customer = serializer.save()
        logger.info("New customer created: ID=%s, Name=%s, Phone=%s, Email=%s",
                    customer.id, customer.name, customer.phone, customer.email)

# CREATE PRODUCT CATEGORIES
class CategoryCreateView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        name = serializer.validated_data.get("name")

        # Check if category with same name exists
        if Category.objects.filter(name__iexact=name).exists():
            raise ValidationError({"name": f"Category '{name}' already exists."})

        category = serializer.save()
        parent_info = f" (Parent ID={category.parent.id}, Name={category.parent.name})" if category.parent else " (No parent)"
        logger.info("New category created: ID=%s, Name=%s%s",
                    category.id, category.name, parent_info)

# CREATE NEW PRODUCTS
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        name = serializer.validated_data.get("name")

        # Check case-insensitive duplicates
        if Product.objects.filter(name__iexact=name).exists():
            raise ValidationError({"name": f"Product '{name}' already exists."})

        product = serializer.save()
        logger.info("New product created: ID=%s, Name=%s, Price=%.2f",
                    product.id, product.name, product.price)


# UPLOAD A SINGLE PRODUCT
class ProductUploadView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def perform_create(self, serializer):
        product = serializer.save()
        logger.info("Product uploaded: ID=%s, Name=%s, Price=%.2f",
                    product.id, product.name, product.price)



# GET AVERAGE PRICE BY CATEGORY
class AveragePriceByCategoryView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        desc = category.get_descendants()
        cat_ids = [category.id] + [d.id for d in desc]

        logger.info("Fetching average price for category ID %s (%s) including %d descendant(s)",
                    category.id, category.name, len(desc))

        products = Product.objects.filter(categories__id__in=cat_ids).distinct()
        if not products.exists():
            logger.warning("No products found for category ID %s (%s)", category.id, category.name)
            return Response({'average_price': None})

        avg = products.aggregate(avg_price=models.Avg('price'))['avg_price']
        logger.info("Average price for category ID %s (%s): %.2f", category.id, category.name, avg)

        return Response({'average_price': float(avg)})


# CREATE NEW ORDER
class OrderCreateView(generics.CreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        items_data = self.request.data.get("items", [])
        if not items_data:
            raise ValidationError({"items": "You must provide at least one product."})

        # Let the serializer handle item creation + totals
        order = serializer.save()

        logger.info("Order %s finalized. Total = %.2f", order.id, order.total)

        # ---- Send SMS ----
        try:
            customer_phone = order.customer.phone
            if customer_phone:
                url = "https://api.sandbox.africastalking.com/version1/messaging"
                headers = {
                    "apikey": settings.AT_API_KEY,
                    "Content-Type": "application/x-www-form-urlencoded"
                }
                data = {
                    "username": settings.AT_USERNAME,
                    "to": customer_phone,
                    "message": f"Hello {order.customer.name}, your order #{order.id} has been placed. Total: {order.total}"
                }
                response = requests.post(url, headers=headers, data=data, verify=False)
                logger.info("SMS response: %s", response.text)
        except Exception as e:
            logger.error("SMS error: %s", e)

        # ---- Send Email ----
        try:
            subject = f"Hello {order.customer.name}, your new order has been placed!"
            body = (
                f"Dear {order.customer.name},\n\n"
                f"Thank you for shopping with us! Your order has been successfully placed.\n\n"
                f"Order Details:\n"
                f"Order ID: {order.id}\n"
                f"Customer: {order.customer.name}\n"
                f"Total Amount: {order.total}\n\n"
                f"Items:\n"
            )
            for it in order.items.all():
                body += f"- {it.product.name} x{it.quantity} @ {it.price}\n"

            body += (
                "\nWe will notify you once your order is out for delivery.\n\n"
                "Best regards,\nSavannah Team"
            )
            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True
            )
            logger.info("Email sent successfully")
        except Exception as e:
            logger.error("Email error: %s", e)


