from django.db import models
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone
from projects.models import Project
from users.models import Employee,CustomUser

class Invoice(models.Model):

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='invoices'
    )

    invoice_number = models.CharField(max_length=100, unique=True)

    issue_date = models.DateField()

    due_date = models.DateField()

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number


class Payment(models.Model):

    PAYMENT_METHOD = (
        ('cash', 'Cash'),
        ('bank', 'Bank Transfer'),
        ('upi', 'UPI'),
        ('cheque', 'Cheque'),
    )

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payments'
    )

    payment_date = models.DateField()

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD
    )

    received_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Payment for {self.invoice.invoice_number}"



class ExpenseReport(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    CATEGORY_CHOICES = (
        ('sales','Sales'),
        ('structure','Project - Structure'),
        ('electrical','Project - Electrical'),
        ('services','Services'),
        ('materials','Materials'),
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="expense_reports"
    )

    expense_date = models.DateField()

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    submitted_by = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True
    )

    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True,null=True)

    @property
    def total_amount(self):
        return self.items.aggregate(total=Sum('amount'))['total'] or 0

    def __str__(self):
        return f"{self.project} - {self.expense_date}"
    



class ExpenseItem(models.Model):

    report = models.ForeignKey(
        ExpenseReport,
        on_delete=models.CASCADE,
        related_name="items"
    )

    description = models.CharField(max_length=200)

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f"{self.description} - {self.amount}"
    
class ExpenseReceipt(models.Model):
    report = models.ForeignKey(ExpenseReport, on_delete=models.CASCADE, related_name="receipts")
    file = models.FileField(upload_to="expense_receipts/")


class DesignCosting(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='design_costing' 
    )

    cost = models.DecimalField(max_digits=12, decimal_places=2)
    design_file = models.FileField(upload_to='design_costs/', null=True, blank=True)
    
    entered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Design Cost - {self.project.title}"
    




class ProjectCosting(models.Model):

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='project_costing'
    )

    design_costing = models.OneToOneField(
        DesignCosting,
        on_delete=models.CASCADE,
        related_name='project_costing',
        null=True
    )

    system_costing = models.DecimalField(max_digits=12, decimal_places=2)

    kseb_cost = models.DecimalField(   
        max_digits=12,
        decimal_places=2,
        default=0
    )

    entered_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    proposal_sent = models.BooleanField(default=False)
    client_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    last_updated = models.DateTimeField(auto_now=True)

    # ✅ TOTAL COST
    @property
    def estimated_cost(self):
        design = self.design_costing.cost if self.design_costing else Decimal('0')
        system = self.system_costing or Decimal('0')
        kseb = self.kseb_cost or Decimal('0')
        return design + system + kseb

    # ✅ ACTUAL COST
    @property
    def actual_cost(self):
        total = self.project.expense_reports.aggregate(
            total=Sum('items__amount')
        )['total']
        return total or Decimal('0')

    # ✅ REVENUE
    @property
    def revenue(self):
        total = self.project.invoices.filter(
            status='paid'
        ).aggregate(
            total=Sum('total_amount')
        )['total']
        return total or Decimal('0')

    # ✅ PROFIT
    @property
    def profit(self):
        return self.revenue - self.actual_cost

    # ✅ APPROVAL METHOD
    def mark_client_approved(self):
        self.client_approved = True
        self.approved_at = timezone.now()
        self.save()

    def __str__(self):
        return f"Costing - {self.project.title}"