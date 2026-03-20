from django.contrib import admin
from .models import *


admin.site.register(Invoice)
admin.site.register(Payment)
admin.site.register(ExpenseReport)
admin.site.register(ExpenseItem)
admin.site.register(ExpenseReceipt)
admin.site.register(ProjectCosting)
