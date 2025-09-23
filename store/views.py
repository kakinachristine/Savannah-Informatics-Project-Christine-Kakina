from django.db import models
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

import africastalking

from .models import Customer, Category, Product, Order
from .serializers import CustomerSerializer, CategorySerializer, ProductSerializer, OrderSerializer

# Initialize Africa's Talking once
if settings.AT_API_KEY and settings.AT_USERNAME:
    africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
    sms = africastalking.SMS
else:
    sms = None


# ----------------- CREATE ENDPOINTS -----------------

class CustomerCreateView(generics.CreateAPIView):
    """Create a new customer"""
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]


class CategoryCreateView(generics.CreateAPIView):
    """Create a new category"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductCreateView(generics.CreateAPIView):
    """Create a new product"""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


# ----------------- EXISTING ENDPOINTS -----------------

class ProductUploadView(generics.CreateAPIView):
    """Upload a single product (optional: handle array)"""
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer


class AveragePriceByCategoryView(generics.GenericAPIView):
    """Return average product price for a category (including descendants)"""
    permission_classes = [AllowAny]

    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        desc = category.get_descendants()
        cat_ids = [category.id] + [d.id for d in desc]

        products = Product.objects.filter(categories__id__in=cat_ids).distinct()
        if not products.exists():
            return Response({'average_price': None})

        avg = products.aggregate(avg_price=models.Avg('price'))['avg_price']
        return Response({'average_price': float(avg)})


class OrderCreateView(generics.CreateAPIView):
    """Place a new order, send SMS + email notifications"""
    serializer_class = OrderSerializer

    def perform_create(self, serializer):
        order = serializer.save()

        # Send SMS to customer
        try:
            customer_phone = order.customer.phone
            if sms and customer_phone:
                sms.send(
                    f"Your order #{order.id} has been placed. Total: {order.total}",
                    [customer_phone]
                )
        except Exception as e:
            print("SMS error:", e)

        # Send admin email
        try:
            subject = f"New Order #{order.id}"
            body = f"Order id: {order.id}\nCustomer: {order.customer}\nTotal: {order.total}\n\nItems:\n"
            for it in order.items.all():
                body += f"- {it.product.name} x{it.quantity} @ {it.price}\n"

            send_mail(
                subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True
            )
        except Exception as e:
            print("Email error:", e)
