from django import forms
from .models import *




class MaterialForm(forms.ModelForm):

    class Meta:
        model = Material
        exclude = ['created_at']

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.TextInput(attrs={"class": "form-control"}),
            "brand": forms.TextInput(attrs={"class": "form-control"}),
            "unit": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "minimum_stock": forms.NumberInput(attrs={"class": "form-control"}),
        }


class VendorForm(forms.ModelForm):

    class Meta:
        model = Vendor
        exclude = ['created_at']


        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "gst_number": forms.TextInput(attrs={"class": "form-control"}),
        }




class PurchaseOrderForm(forms.ModelForm):

    class Meta:
        model = PurchaseOrder
        exclude = ['total_amount','created_at']

        widgets = {
            "vendor": forms.Select(attrs={"class": "form-select"}),
            "order_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "expected_delivery": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }



class PurchaseOrderItemForm(forms.ModelForm):

    class Meta:
        model = PurchaseOrderItem
        exclude = ['purchase_order']


        widgets = {
            "material": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control"}),
        }



class GoodsReceivedForm(forms.ModelForm):

    class Meta:
        model = GoodsReceived
        exclude = ['created_at']


        widgets = {
            "purchase_order": forms.Select(attrs={"class": "form-select"}),
            "received_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "received_by": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }



class MaterialAllocationRequestForm(forms.ModelForm):

    class Meta:
        model = MaterialAllocation
        fields = ['project', 'material', 'quantity']   

        widgets = {
            "project": forms.Select(attrs={"class": "form-select"}),
            "material": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
        }
        

class MaterialAllocationForm(forms.ModelForm):
    class Meta:
        model = MaterialAllocation
        fields = ['status']  # only allow status change
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
        }