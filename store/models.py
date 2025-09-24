from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE,
    )

    class Meta:
        unique_together = ("parent", "name")
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_descendants(self):
        """Return a list of all descendant categories (recursive)."""
        descendants = []
        children = list(self.children.all())
        while children:
            next_children = []
            for c in children:
                descendants.append(c)
                next_children.extend(list(c.children.all()))
            children = next_children
        return descendants


class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    categories = models.ManyToManyField(Category, related_name="products")

    def __str__(self):
        return f"{self.name} ({self.price})"


class Order(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, related_name="orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.TextField(blank=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer} - {self.total}"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # ✅ Add this

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

