from django.urls import path
from .views import (
    CustomerCreateView,
    CategoryCreateView,
    ProductCreateView,
    ProductUploadView,
    AveragePriceByCategoryView,
    OrderCreateView
)
urlpatterns = [
    path("products/upload/", ProductUploadView.as_view(), name="product-upload"),
    path("categories/<int:category_id>/average-price/", AveragePriceByCategoryView.as_view(), name="average-price"),
    path("orders/create/", OrderCreateView.as_view(), name="order-create"),
    path("customers/create/", CustomerCreateView.as_view(), name="create-customer"),
    path("categories/create/", CategoryCreateView.as_view(), name="create-category"),
    path("products/create/", ProductCreateView.as_view(), name="create-product"),
]
