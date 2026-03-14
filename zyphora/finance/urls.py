from django.urls import path
from .views import *


urlpatterns = [

    # ---------------- INVOICES ---------------- #
    path("invoices/", invoice_list, name="invoice_list"),
    path("create-invoice/", create_invoice, name="create_invoice"),
    path("edit-invoice/<int:pk>/", update_invoice, name="edit_invoice"),
    path("delete-invoice/<int:pk>/", delete_invoice, name="delete_invoice"),

    # ---------------- PAYMENTS ---------------- #
    path("payments/", payment_list, name="payment_list"),
    path("create-payment/", create_payment, name="create_payment"),

    # ---------------- EXPENSES ---------------- #
    path("expenses/", expense_list, name="expense_list"),
    path("create-expense/", create_expense, name="create_expense"),
    path("approve-expense/<int:pk>/", approve_expense, name="approve_expense"),
    path("reject-expense/<int:pk>/", reject_expense, name="reject_expense"),

    # ---------------- PROJECT COSTING ---------------- #
    path("project-costing/", project_costing, name="project_costing"),

    # ---------------- FINANCIAL REPORTS ---------------- #
    path("reports/", finance_reports, name="finance_reports"),

]