from django.urls import path
from .views import *

urlpatterns = [

    # INVOICE MANAGEMENT
    path("invoices/", invoice_list, name="invoice_list"),
    path("invoices/draft/", invoice_draft, name="invoice_draft"),
    path("invoices/sent/", invoice_sent, name="invoice_sent"),
    path("invoices/paid/", invoice_paid, name="invoice_paid"),
    path("invoices/overdue/", invoice_overdue, name="invoice_overdue"),
    path("create-invoice/", create_invoice, name="create_invoice"),
    path("edit-invoice/<int:pk>/", update_invoice, name="edit_invoice"),
    path("delete-invoice/<int:pk>/", delete_invoice, name="delete_invoice"),

    # PAYMENTS
    path("payments/", client_payments, name="client_payments"),
    path("payments/pending/", pending_receivables, name="pending_receivables"),
    path("payments/confirmations/", payment_confirmations, name="payment_confirmations"),
    path("revenue/overview/", revenue_overview, name="revenue_overview"),
    path("create-payment/", create_payment, name="create_payment"),

    # EXPENSES
    path("expenses/", all_expenses, name="all_expenses"),
    path("expenses/pending/", pending_expenses, name="pending_expenses"),
    path("expenses/approved/", approved_expenses, name="approved_expenses"),
    path("expenses/rejected/", rejected_expenses, name="rejected_expenses"),
    path("my-expenses/", my_expenses, name="my_expenses"),

    path("create-expense/",create_expense,name='create_expense'),
    path("expense-detail/<int:expense_id>/", expense_detail, name="expense_detail"),
    path("approve-expense/<int:pk>/", approve_expense, name="approve_expense"),
    path("approve-all-expenses/", approve_all_expenses, name="approve_all"),
    path("reject-expense/<int:pk>/", reject_expense, name="reject_expense"),

    # FUND RELEASE
    path("funds/history/", expense_history, name="expense_history"),
    path("funds/requests/", fund_release_requests, name="fund_release_requests"),
    path("funds/approved/", approved_fund_releases, name="approved_fund_releases"),

    # PROJECT BUDGET
    path("budget/projects/", project_budgets, name="project_budgets"),
    path("budget/vs_actual/", budget_vs_actual, name="budget_vs_actual"),
    path("budget/remaining/", remaining_budget, name="remaining_budget"),
    path("budget/overrun/", cost_overrun_alerts, name="cost_overrun_alerts"),

    # FINANCIAL REPORTS
    path("reports/monthly-expense/", monthly_expense_report, name="monthly_expense_report"),
    path("reports/project-profit/", project_profit_report, name="project_profit_report"),
    path("reports/cashflow/", cash_flow_summary, name="cash_flow_summary"),
    path("reports/gst-tax/", gst_tax_reports, name="gst_tax_reports"),

    path("costing/",project_costing,name="project_costing")
]