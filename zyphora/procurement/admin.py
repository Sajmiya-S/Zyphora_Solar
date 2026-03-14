from django.contrib import admin
from .models import *


admin.site.register(Material)
admin.site.register(Vendor)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(Stock)
admin.site.register(MaterialAllocation)
admin.site.register(GoodsReceived)



