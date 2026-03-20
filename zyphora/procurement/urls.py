from django.urls import path
from .views import *


urlpatterns = [

    path('vendors/', vendor_list, name="vendor_list"),
    path('add-vendors/', add_vendor, name="add_vendor"),
    path('vendors/<int:vid>/edit/', edit_vendor, name='edit_vendor'),
    path('vendors/<int:vid>/delete/', delete_vendor, name='delete_vendor'),
    path("vendors/<int:vid>/",view_vendor,name="view_vendor"),

    path('materials/', material_list, name="material_list"),
    path('edit-material/<int:mid>/', edit_material, name="edit_material"),
    path('delete-material/<int:mid>', delete_material, name="delete_material"),
    path('add-materials/', add_material, name="add_material"),

    path('material-requests/', admin_material_requests, name="admin_material_requests"),
    path('request-material/', request_material, name="request_material"),
    path('my-requests/', my_requests, name="my_requests"),

    path('purchase-orders/', purchase_order_list, name="purchase_order_list"),
    path('purchase-orders/<int:oid>/', purchase_order_detail, name='purchase_order_detail'),
    path('purchase-orders/<int:oid>/receive/', receive_purchase_order, name='receive_purchase_order'),
    path('purchase-orders/<int:oid>/cancel/', cancel_purchase_order, name='cancel_purchase_order'),
    path('create-purchase-orders/', create_purchase_order, name="create_purchase_order"),

    path('goods-received/', goods_received_list, name="goods_received_list"),
    path('add-goods-received/', add_goods_received, name="add_goods_received"),

    path('stock/', stock_list, name="stock_list"),

    path('allocation/', allocation_list, name="allocation_list"),
    path('add-allocation/', allocate_material, name="allocate_material"),

]