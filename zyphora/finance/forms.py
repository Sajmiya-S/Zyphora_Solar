from django import forms
from .models import *

class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = [
            "project",
            "invoice_number",
            "issue_date",
            "due_date",
            "total_amount",
            "status",
            "notes",
        ]


class PaymentForm(forms.ModelForm):

    class Meta:
        model = Payment
        fields = [
            "invoice",
            "payment_date",
            "amount",
            "method",
            "received_by",
            "notes",
        ]


class ExpenseForm(forms.ModelForm):

    class Meta:
        model = ExpenseReport
        fields = ['project', 'expense_date', 'category', 'notes']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'expense_date': forms.DateInput(attrs={'class': 'form-control', 'type':'date'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control'}),
        }

class ExpenseItemForm(forms.ModelForm):
    class Meta:
        model = ExpenseItem
        fields = ['description', 'amount']
        widgets = {
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter item description'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount', 'step':'0.01'}),
        }

class ExpenseReceiptForm(forms.ModelForm):

    class Meta:
        model = ExpenseReceipt
        fields = ["file"]

        widgets = {
            "file": forms.ClearableFileInput(attrs={
                "class": "form-control"
            })
        }