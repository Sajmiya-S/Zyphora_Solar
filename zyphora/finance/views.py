from django.shortcuts import render, redirect, get_object_or_404
from .models import Invoice, Payment, ExpenseReport
from .forms import InvoiceForm, PaymentForm, ExpenseForm
from projects.models import Project


# ---------------- INVOICE CRUD ---------------- #

def invoice_list(request):

    invoices = Invoice.objects.all().order_by("-issue_date")

    return render(request, "dashboard/invoices.html", {
        "invoices": invoices
    })


def create_invoice(request):

    form = InvoiceForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("invoice_list")

    return render(request, "dashboard/invoice_form.html", {
        "form": form,
        "title": "Add Invoice"
    })


def update_invoice(request, pk):

    invoice = get_object_or_404(Invoice, pk=pk)

    form = InvoiceForm(request.POST or None, instance=invoice)

    if form.is_valid():
        form.save()
        return redirect("invoice_list")

    return render(request, "dashboard/invoice_form.html", {
        "form": form,
        "title": "Edit Invoice"
    })


def delete_invoice(request, pk):

    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == "POST":
        invoice.delete()
        return redirect("invoice_list")

    return redirect(invoice_list)


# ---------------- PAYMENTS ---------------- #

def payment_list(request):

    payments = Payment.objects.all()

    return render(request, "dashboard/payments.html", {
        "payments": payments
    })


def create_payment(request):

    form = PaymentForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("payment_list")

    return render(request, "dashboard/payment_form.html", {
        "form": form,
        "title": "Add Payment"
    })


# ---------------- EXPENSES ---------------- #

def expense_list(request):

    expenses = ExpenseReport.objects.all()

    return render(request, "dashboard/expenses.html", {
        "expenses": expenses
    })


def create_expense(request):

    form = ExpenseForm(request.POST or None)

    if form.is_valid():
        form.save()
        return redirect("expense_list")

    return render(request, "dashboard/expense_form.html", {
        "form": form,
        "title": "Add Expense"
    })

def approve_expense(request,pk):
    expense = get_object_or_404(ExpenseReport, pk=pk)

    expense.status = "approved"
    expense.save()

    return redirect("expense_list")


def reject_expense(request, pk):

    expense = get_object_or_404(ExpenseReport, pk=pk)

    expense.status = "rejected"
    expense.save()

    return redirect("expense_list")



# ---------------- PROJECT COSTING ---------------- #

def project_costing(request):

    projects = Project.objects.all()

    return render(request, "dashboard/costing.html", {
        "projects": projects
    })


# ---------------- REPORTS ---------------- #

def finance_reports(request):

    invoices = Invoice.objects.count()
    payments = Payment.objects.count()
    expenses = ExpenseReport.objects.count()

    return render(request, "dashboard/reports.html", {
        "invoice_count": invoices,
        "payment_count": payments,
        "expense_count": expenses
    })

