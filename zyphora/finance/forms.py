from django import forms
from .models import Invoice, Payment, ExpenseReport


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
        fields = [
            "project",
            "expense_date",
            "category",
            "submitted_by",
            "notes",
            "status",
        ]