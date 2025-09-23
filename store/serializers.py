from rest_framework import serializers
from .models import Customer, Category, Product, Order, OrderItem



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "parent"]


class ProductSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all()
    )

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price", "categories"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'name', 'email', 'phone']


class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = OrderItem
        fields = ["product", "quantity", "price"]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "created_at", "total", "note", "items"]
        read_only_fields = ["created_at", "total"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)

        total = 0
        for item_data in items_data:
            product = item_data["product"]
            qty = item_data.get("quantity", 1)
            price = product.price

            OrderItem.objects.create(
                order=order, product=product, quantity=qty, price=price
            )
            total += price * qty

        order.total = total
        order.save()
        return order
