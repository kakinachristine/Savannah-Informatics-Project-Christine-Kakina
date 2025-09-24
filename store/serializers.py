from rest_framework import serializers
from .models import Customer, Category, Product, Order, OrderItem



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name",]


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


class OrderItemInputSerializer(serializers.Serializer):
    product = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemInputSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "customer", "total", "items"]
        read_only_fields = ["id", "total"]

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = Order.objects.create(total=0, **validated_data)

        total_amount = 0
        for item in items_data:
            product_name = item["product"]
            quantity = item.get("quantity", 1)

            products = Product.objects.filter(name__iexact=product_name)
            if not products.exists():
                raise serializers.ValidationError({"product": f"Product '{product_name}' not found."})
            if products.count() > 1:
                raise serializers.ValidationError({"product": f"Multiple products found with name '{product_name}'. Please use a unique identifier."})

            product = products.first()

            # Calculate total
            line_total = product.price * quantity
            total_amount += line_total

            # Save order item with subtotal
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                price=product.price,
                subtotal=line_total,
            )

        # Save grand total
        order.total = total_amount
        order.save()
        return order