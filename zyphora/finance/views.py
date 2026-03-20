from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.db.models.functions import TruncMonth, Cast
from django.db.models import F, Sum, DecimalField
from decimal import Decimal
from django.urls import reverse
from .models import *
from .forms import *
from projects.models import Project
from users.models import Employee, CustomUser
from users.utils import create_notification

# ---------------- INVOICES ---------------- #

@login_required(login_url='/users/login')
def invoice_list(request):
    invoices = Invoice.objects.all().order_by("-issue_date")
    return render(request, "dashboard/accountant/invoices.html", {"invoices": invoices})

@login_required(login_url='/users/login')
def invoice_draft(request):
    invoices = Invoice.objects.filter(status='draft')
    return render(request, "dashboard/accountant/invoices.html", {"invoices": invoices})

@login_required(login_url='/users/login')
def invoice_sent(request):
    invoices = Invoice.objects.filter(status='sent')
    return render(request, "dashboard/accountant/invoices.html", {"invoices": invoices})

@login_required(login_url='/users/login')
def invoice_paid(request):
    invoices = Invoice.objects.filter(status='paid')
    return render(request, "dashboard/accountant/invoices.html", {"invoices": invoices})

@login_required(login_url='/users/login')
def invoice_overdue(request):
    invoices = Invoice.objects.filter(status='overdue')
    return render(request, "dashboard/accountant/invoices.html", {"invoices": invoices})

@login_required(login_url='/users/login')
def create_invoice(request):
    form = InvoiceForm(request.POST or None)
    if form.is_valid():
        invoice = form.save()
        # Notifications
        admins = CustomUser.objects.filter(role='admin')
        accountants = CustomUser.objects.filter(role='accountant')
        for user in list(admins) + list(accountants):
            create_notification(
                recipient=user,
                title="New Invoice Created",
                message=f"Invoice {invoice.invoice_number} has been created.",
                sender=request.user,
                link=reverse("invoice_list"),
                category="invoice"
            )
        create_notification(
            recipient=request.user,
            title="Invoice Created",
            message=f"You created invoice {invoice.invoice_number}.",
            sender=None,
            link=reverse("invoice_list"),
            category="invoice"
        )
        return redirect("invoice_list")
    return render(request, "dashboard/accountant/invoice_form.html", {"form": form, "title": "Add Invoice"})


@login_required(login_url='/users/login')
def update_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    form = InvoiceForm(request.POST or None, instance=invoice)
    if form.is_valid():
        invoice = form.save()
        # Notifications
        admins = CustomUser.objects.filter(role='admin')
        accountants = CustomUser.objects.filter(role='accountant')
        for user in list(admins) + list(accountants):
            create_notification(
                recipient=user,
                title="Invoice Updated",
                message=f"Invoice {invoice.invoice_number} has been updated.",
                sender=request.user,
                link=reverse("invoice_list"),
                category="invoice"
            )
        create_notification(
            recipient=request.user,
            title="Invoice Updated",
            message=f"You updated invoice {invoice.invoice_number}.",
            sender=None,
            link=reverse("invoice_list"),
            category="invoice"
        )
        return redirect("invoice_list")
    return render(request, "dashboard/accountant/invoice_form.html", {"form": form, "title": "Edit Invoice"})


@login_required(login_url='/users/login')
def delete_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if request.method == "POST":
        invoice.delete()
        return redirect("invoice_list")
    return redirect("invoice_list")


# ---------------- PAYMENTS ---------------- #

@login_required(login_url='/users/login')
def client_payments(request):
    payments = Payment.objects.all()
    return render(request, "dashboard/accountant/payments.html", {"payments": payments})

@login_required(login_url='/users/login')
def pending_receivables(request):
    payments = Payment.objects.filter(invoice__status__in=['draft','sent'])
    return render(request, "dashboard/accountant/payments.html", {"payments": payments})

@login_required(login_url='/users/login')
def payment_confirmations(request):
    payments = Payment.objects.filter(invoice__status='paid')
    return render(request, "dashboard/accountant/payments.html", {"payments": payments})

@login_required(login_url='/users/login')
def revenue_overview(request):
    projects = Project.objects.all()
    return render(request, "dashboard/accountant/revenue_overview.html", {"projects": projects})

@login_required(login_url='/users/login')
def create_payment(request):
    form = PaymentForm(request.POST or None)
    if form.is_valid():
        payment = form.save()
        # Notifications
        admins = CustomUser.objects.filter(role='admin')
        accountants = CustomUser.objects.filter(role='accountant')
        for user in list(admins) + list(accountants):
            create_notification(
                recipient=user,
                title="New Payment Recorded",
                message=f"Payment of ₹{payment.amount} received for invoice {payment.invoice.invoice_number}.",
                sender=request.user,
                link=reverse("client_payments"),
                category="payment"
            )
        create_notification(
            recipient=request.user,
            title="Payment Recorded",
            message=f"You recorded a payment of ₹{payment.amount} for invoice {payment.invoice.invoice_number}.",
            sender=None,
            link=reverse("client_payments"),
            category="payment"
        )
        return redirect("client_payments")
    return render(request, "dashboard/accountant/payment_form.html", {"form": form, "title": "Add Payment"})


# ---------------- EXPENSES ---------------- #

@login_required(login_url='/users/login')
def all_expenses(request):
    expenses = ExpenseReport.objects.all()
    return render(request, "dashboard/accountant/expenses.html", {"expenses": expenses})

@login_required(login_url='/users/login')
def pending_expenses(request):
    expenses = ExpenseReport.objects.filter(status='pending')
    return render(request, "dashboard/accountant/expenses.html", {"expenses": expenses})

@login_required(login_url='/users/login')
def approved_expenses(request):
    expenses = ExpenseReport.objects.filter(status='approved')
    return render(request, "dashboard/accountant/expenses.html", {"expenses": expenses})

@login_required(login_url='/users/login')
def rejected_expenses(request):
    expenses = ExpenseReport.objects.filter(status='rejected')
    return render(request, "dashboard/accountant/expenses.html", {"expenses": expenses})

# ---------------- EXPENSE ACTIONS ---------------- #


@login_required(login_url='/users/login')
def create_expense(request):
    # Main expense form
    form = ExpenseForm(request.POST or None)

    # Inline formsets
    ItemFormSet = inlineformset_factory(
        ExpenseReport,
        ExpenseItem,
        form=ExpenseItemForm,
        fields=('description', 'amount'),
        extra=1,
        can_delete=True
    )
    ReceiptFormSet = inlineformset_factory(
        ExpenseReport,
        ExpenseReceipt,
        form=ExpenseReceiptForm,
        extra=1,
        can_delete=True
    )

    item_formset = ItemFormSet(request.POST or None, prefix='items')
    receipt_formset = ReceiptFormSet(request.POST or None, request.FILES or None, prefix='receipts')

    if form.is_valid() and item_formset.is_valid() and receipt_formset.is_valid():
        expense = form.save(commit=False)
        expense.submitted_by = request.user.employee
        expense.status = 'pending'
        expense.save()

        # Save formsets
        item_formset.instance = expense
        item_formset.save()
        receipt_formset.instance = expense
        receipt_formset.save()

        # Notify admins/accountants
        admins = CustomUser.objects.filter(role='admin')
        accountants = CustomUser.objects.filter(role='accountant')
        for user in list(admins) + list(accountants):
            create_notification(
                recipient=user,
                title="New Expense Report Submitted",
                message=f"{request.user.get_full_name()} submitted a new expense report.",
                sender=request.user,
                link=reverse('expense_detail', args=[expense.id]),
                category='expense'
            )

        return redirect('my_expenses')

    context = {
        'form': form,
        'item_formset': item_formset,
        'receipt_formset': receipt_formset,
        'title': 'Add Expense Report',
    }
    return render(request, 'dashboard/accountant/create_expense.html', context)


@login_required(login_url='/users/login')
def my_expenses(request):
    expenses = ExpenseReport.objects.filter(
        submitted_by=request.user.employee
    ).prefetch_related("items", "receipts").order_by("-created_at")
    return render(request, "dashboard/accountant/my_expenses.html", {"expenses": expenses})


@login_required(login_url='/users/login')
def expense_detail(request, expense_id):
    expense = get_object_or_404(ExpenseReport, id=expense_id)
    items = expense.items.all()
    receipts = expense.receipts.all()
    total_amount = sum(item.amount for item in items)

    context = {
        "expense": expense,
        "items": items,
        "receipts": receipts,
        "total_amount": total_amount,
    }
    return render(request, "dashboard/accountant/expense_detail.html", context)


@login_required(login_url='/users/login')
def approve_expense(request, pk):
    expense = get_object_or_404(ExpenseReport, pk=pk)
    expense.status = "approved"
    expense.save()

    # ---------------- NOTIFICATIONS ---------------- #
    # Notify submitting user
    create_notification(
        recipient=expense.submitted_by.user,
        title="Expense Report Approved ✅",
        message=f"Your expense report of ₹{expense.total_amount} has been approved.",
        sender=request.user,
        link=reverse("expense_detail", args=[expense.id]),
        category="expense"
    )

    # Notify admins and accountants
    admins = CustomUser.objects.filter(role='admin')
    accountants = CustomUser.objects.filter(role='accountant')
    for user in list(admins) + list(accountants):
        create_notification(
            recipient=user,
            title="Expense Report Approved",
            message=f"{expense.submitted_by.user.get_full_name()}'s expense report has been approved by {request.user.get_full_name()}.",
            sender=request.user,
            link=reverse("expense_detail", args=[expense.id]),
            category="expense"
        )

    return redirect("expense_list")


@login_required(login_url='/users/login')
def reject_expense(request, pk):
    expense = get_object_or_404(ExpenseReport, pk=pk)
    expense.status = "rejected"
    expense.save()

    # ---------------- NOTIFICATIONS ---------------- #
    # Notify submitting user
    create_notification(
        recipient=expense.submitted_by.user,
        title="Expense Report Rejected ❌",
        message=f"Your expense report of ₹{expense.total_amount} has been rejected.",
        sender=request.user,
        link=reverse("expense_detail", args=[expense.id]),
        category="expense"
    )

    # Notify admins and accountants
    admins = CustomUser.objects.filter(role='admin')
    accountants = CustomUser.objects.filter(role='accountant')
    for user in list(admins) + list(accountants):
        create_notification(
            recipient=user,
            title="Expense Report Rejected",
            message=f"{expense.submitted_by.user.get_full_name()}'s expense report has been rejected by {request.user.get_full_name()}.",
            sender=request.user,
            link=reverse("expense_detail", args=[expense.id]),
            category="expense"
        )

    return redirect("expense_list")



# ---------------- FUND RELEASE ---------------- #

@login_required(login_url='/users/login')
def expense_history(request):
    # Replace with real queryset
    expenses = ExpenseReport.objects.all()
    return render(request, "dashboard/accountant/fund_history.html", {"expenses": expenses})

@login_required(login_url='/users/login')
def fund_release_requests(request):
    expenses = ExpenseReport.objects.all()
    return render(request, "dashboard/accountant/fund_requests.html", {"expenses": expenses})

@login_required(login_url='/users/login')
def approved_fund_releases(request):
    # Replace with real queryset
    expenses = ExpenseReport.objects.filter(status='approved')
    return render(request, "dashboard/accountant/fund_approved.html", {"expenses": expenses})


# ---------------- PROJECT BUDGET ---------------- #


@login_required(login_url='/users/login')
def project_budgets(request):
    # Prefetch related costing and expense reports/items for efficient access
    projects = Project.objects.prefetch_related(
        'costing',
        'expense_reports__items',
        'invoices'
    )

    project_data = []

    for project in projects:
        costing = getattr(project, 'costing', None)
        estimated = costing.estimated_cost if costing else 0

        # Actual cost: sum of all expense items
        actual = project.expense_reports.aggregate(
            total=Sum('items__amount')
        )['total'] or 0

        remaining = estimated - actual
        project_data.append({
            'project': project,
            'estimated_cost': estimated,
            'actual_cost': actual,
            'remaining_budget': remaining,
        })

    return render(request, "dashboard/accountant/project_budgets.html", {"projects": project_data})


@login_required(login_url='/users/login')
def budget_vs_actual(request):
    # Prefetch for efficiency
    projects = Project.objects.prefetch_related(
        'costing',
        'expense_reports__items',
        'invoices'
    )

    project_data = []

    for project in projects:
        costing = getattr(project, 'costing', None)
        estimated = costing.estimated_cost if costing else 0

        actual = project.expense_reports.aggregate(
            total=Sum('items__amount')
        )['total'] or 0

        revenue = project.invoices.filter(status='paid').aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        profit = revenue - actual

        project_data.append({
            'project': project,
            'estimated_cost': estimated,
            'actual_cost': actual,
            'revenue': revenue,
            'profit': profit,
        })

    return render(request, "dashboard/accountant/budget_vs_actual.html", {"projects": project_data})


@login_required(login_url='/users/login')
def remaining_budget(request):
    projects = Project.objects.prefetch_related(
        'costing',
        'expense_reports__items'
    )

    project_data = []

    for project in projects:
        costing = getattr(project, 'costing', None)
        estimated = costing.estimated_cost if costing else 0
        actual = project.expense_reports.aggregate(total=Sum('items__amount'))['total'] or 0
        remaining = estimated - actual

        project_data.append({
            'project': project,
            'remaining_budget': remaining
        })

    return render(request, "dashboard/accountant/remaining_budget.html", {"projects": project_data})


@login_required(login_url='/users/login')
def cost_overrun_alerts(request):
    projects = Project.objects.prefetch_related(
        'costing',
        'expense_reports__items'
    )

    overrun_projects = []

    for project in projects:
        costing = getattr(project, 'costing', None)
        if not costing:
            continue

        actual = project.expense_reports.aggregate(total=Sum('items__amount'))['total'] or 0
        if actual > costing.estimated_cost:
            overrun_projects.append({
                'project': project,
                'estimated_cost': costing.estimated_cost,
                'actual_cost': actual,
                'overrun_amount': actual - costing.estimated_cost
            })

    return render(request, "dashboard/accountant/cost_overrun.html", {"projects": overrun_projects})


# ---------------- FINANCIAL REPORTS ---------------- #


# ---------------- Monthly Expense Report ---------------- #
@login_required(login_url='/users/login')
def monthly_expense_report(request):
    # Annotate each expense report by month
    expenses = ExpenseReport.objects.annotate(
        month=TruncMonth('expense_date')
    ).values('month').annotate(
        total_amount=Sum('items__amount')
    ).order_by('-month')

    return render(request, "dashboard/accountant/monthly_expense_report.html", {"expenses": expenses})


# ---------------- Project Profit Report ---------------- #
@login_required(login_url='/users/login')
def project_profit_report(request):
    projects = Project.objects.prefetch_related(
        'invoices',
        'expense_reports__items',
        'costing'
    )
    report_data = []

    for project in projects:
        # Safely get estimated cost
        estimated = getattr(project.costing, 'estimated_cost', 0)

        # Actual expenses
        actual = project.expense_reports.aggregate(total=Sum('items__amount'))['total'] or 0

        # Revenue from paid invoices
        revenue = project.invoices.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0

        profit = revenue - actual

        report_data.append({
            'project': project,
            'estimated_cost': estimated,
            'actual_cost': actual,
            'revenue': revenue,
            'profit': profit,
        })

    return render(request, "dashboard/accountant/project_profit_report.html", {"projects": report_data})


# ---------------- Cash Flow Summary ---------------- #
@login_required(login_url='/users/login')
def cash_flow_summary(request):
    total_received = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0
    total_expenses = ExpenseReport.objects.aggregate(total=Sum('items__amount'))['total'] or 0
    net_cash_flow = total_received - total_expenses

    context = {
        'total_received': total_received,
        'total_expenses': total_expenses,
        'net_cash_flow': net_cash_flow
    }
    return render(request, "dashboard/accountant/cash_flow_summary.html", context)


# ---------------- GST / Tax Reports ---------------- #
@login_required(login_url='/users/login')
def gst_tax_reports(request):
    gst_rate = Decimal('0.18')  # 18% GST

    # Safe annotation for DecimalField
    invoices = Invoice.objects.filter(status='paid').annotate(
        gst_amount=Cast(
            F('total_amount') * gst_rate,
            DecimalField(max_digits=12, decimal_places=2)
        )
    )

    total_gst = invoices.aggregate(total=Sum('gst_amount'))['total'] or 0

    return render(request, "dashboard/accountant/gst_tax_reports.html", {
        'invoices': invoices,
        'total_gst': total_gst,
        'gst_rate': gst_rate * 100
    })



from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import ProjectCosting
from projects.models import Project

@login_required(login_url='/users/login')
def project_costing(request):
    projects = Project.objects.all()

    costing_data = []

    for project in projects:
        costing, created = ProjectCosting.objects.get_or_create(
            project=project,
            defaults={"estimated_cost": 0}
        )

        costing_data.append({
            "project": project,
            "estimated_cost": costing.estimated_cost,
            "actual_cost": costing.actual_cost(),
            "revenue": costing.revenue(),
            "profit": costing.profit(),
        })

    context = {
        "costing_data": costing_data
    }

    return render(request, "dashboard/admin/project_costing.html", context)