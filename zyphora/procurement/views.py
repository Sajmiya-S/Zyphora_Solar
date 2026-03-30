from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.forms import modelformset_factory
from django.core.paginator import Paginator
from django.http import JsonResponse
from collections import defaultdict

from .models import *
from .forms import *

from users.utils import create_notification




@login_required(login_url='/users/login')
def material_list(request):
    query = request.GET.get("q")
    category = request.GET.get("category")

    materials = Material.objects.select_related("stock")

    # Search
    if query:
        materials = materials.filter(
            Q(name__icontains=query) |
            Q(brand__icontains=query)
        )

    # Category filter
    if category:
        materials = materials.filter(category=category)

    context = {
        "materials": materials,
        "category_choices": Material.CATEGORY_CHOICES,
        "category": category,
    }

    return render(request, "dashboard/material_list.html", context)


def edit_material(request, mid):
    material = Material.objects.get(id=mid)

    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            return redirect(material_list)  
    else:
        form = MaterialForm(instance=material)
    
    return render(request, "dashboard/edit_material.html", {"form": form, "material": material})


def delete_material(request, mid):
    material = Material.objects.get(id=mid)
    
    if request.method == "POST":
        material.delete()
        
    return redirect('material_list')

@login_required(login_url='/users/login')
def add_material(request):

    form = MaterialForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Material created successfully")
        return redirect("material_list")

    return render(request, "dashboard/add_material.html", {"form": form})



@login_required(login_url='/users/login')
def vendor_list(request):

    query = request.GET.get("q")

    vendors = Vendor.objects.all()

    if query:
        vendors = vendors.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query)
        )

    return render(request, "dashboard/vendor_list.html", {"vendors": vendors})

def view_vendor(request, vid):

    vendor = get_object_or_404(Vendor, id=vid)

    context = {
        "vendor": vendor
    }

    return render(request, "dashboard/view_vendor.html", context)

@login_required(login_url='/users/login')
def add_vendor(request):

    form = VendorForm(request.POST or None)

    if form.is_valid():
        form.save()
        messages.success(request, "Vendor added successfully")
        return redirect("vendor_list")

    return render(request, "dashboard/add_vendor.html", {"form": form})

def edit_vendor(request, vid):
    vendor = get_object_or_404(Vendor, id=vid)
    
    if request.method == "POST":
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            return redirect(vendor_list) 
    else:
        form = VendorForm(instance=vendor)
    
    return render(request, "dashboard/edit_vendor.html", {"form": form, "vendor": vendor})


def delete_vendor(request, vid):
    vendor = get_object_or_404(Vendor, id=vid)
    
    if request.method == "POST":
        vendor.delete()
    
    return redirect(vendor_list)


@login_required(login_url='/users/login')
def purchase_order_list(request):

    query = request.GET.get('q', '')
    today = timezone.localdate()

    if query:
        purchase_orders = PurchaseOrder.objects.filter(
            Q(id__icontains=query) | Q(vendor__name__icontains=query)
        ).order_by('-order_date')
    else:
        purchase_orders = PurchaseOrder.objects.all().order_by('-order_date')

    # Add overdue days dynamically
    for po in purchase_orders:
        if po.expected_delivery and po.expected_delivery < today and po.status not in ['received', 'cancelled']:
            po.overdue_days = (today - po.expected_delivery).days
        else:
            po.overdue_days = 0

    context = {
        "purchase_orders": purchase_orders,
        "today": today
    }

    return render(request, "dashboard/purchase_order_list.html", context)


@login_required(login_url='/users/login/')
def purchase_order_detail(request,oid):
    po = get_object_or_404(PurchaseOrder, id=oid)
    items = po.items.all()
    today = timezone.localdate()

    context = {
        "po": po,
        "items": items,
        "today": today
    }
    return render(request, 'dashboard/purchase_order_detail.html', context)


@login_required(login_url='/users/login/')
def receive_purchase_order(request, oid):
    po = get_object_or_404(PurchaseOrder, id=oid)

    if po.status not in ['received', 'cancelled']:
        po.status = 'received'
        po.save()

    return redirect('purchase_orders_list')


@login_required(login_url='/users/login/')
def cancel_purchase_order(request,oid):
    po = get_object_or_404(PurchaseOrder, id=oid)

    if po.status not in ['received', 'cancelled']:
        po.status = 'cancelled'
        po.save()

    return redirect('purchase_orders_list')


@login_required(login_url='/users/login')
def create_purchase_order(request):

    if request.method == "POST":

        form = PurchaseOrderForm(request.POST)

        if form.is_valid():

            po = form.save(commit=False)
            po.total_amount = 0
            po.save()

            materials = request.POST.getlist("material[]")
            quantities = request.POST.getlist("quantity[]")
            prices = request.POST.getlist("price[]")

            for material, qty, price in zip(materials, quantities, prices):

                if material and qty and price:

                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        material_id=material,
                        quantity=int(qty),
                        unit_price=float(price)
                    )

            # update total
            po.update_total()

            messages.success(request, "Purchase Order created successfully")

            return redirect("purchase_order_list")

    else:
        form = PurchaseOrderForm()

    materials = Material.objects.all()

    context = {
        "form": form,
        "materials": materials
    }

    return render(request, "dashboard/create_purchase_order.html", context)



@login_required(login_url='/users/login')
def goods_received_list(request):

    
    q = request.GET.get("q")

    goods = GoodsReceived.objects.select_related(
        "purchase_order",
        "purchase_order__vendor",
        "received_by"
    ).order_by("-created_at")
    from datetime import date

    today = date.today()
    for g in goods:
        g.days_since_received = (today - g.received_date).days

    if q:
        goods = goods.filter(
            Q(purchase_order__id__icontains=q) |
            Q(purchase_order__vendor__name__icontains=q)
        )


    return render(request, "dashboard/goods_received_list.html", {"goods": goods})




@login_required(login_url='/users/login')
def add_goods_received(request):

    oid = request.GET.get('po')
    initial_data = {}
    if oid:
        initial_data['purchase_order'] = oid

    if request.method == "POST":
        form = GoodsReceivedForm(request.POST)
        if form.is_valid():
            goods = form.save()
            # Update PO status to received
            po = goods.purchase_order
            po.status = 'received'
            po.save()
            return redirect('purchase_orders_list')
    else:
        form = GoodsReceivedForm(initial=initial_data)

    return render(request, "dashboard/add_goods_received.html", {"form": form})


@login_required(login_url='/users/login')
def stock_list(request):

    q = request.GET.get("q")

    stocks = Stock.objects.select_related("material").order_by("material__name")

    if q:
        stocks = stocks.filter(
            Q(material__name__icontains=q) |
            Q(material__brand__icontains=q)
        )

    return render(request, "dashboard/stock_list.html", {"stocks": stocks })




@login_required(login_url='/users/login')
def allocation_list(request):

    q = request.GET.get("q")

    allocations = MaterialAllocation.objects.select_related(
        "project",
        "material",
        "allocated_by"
    ).order_by("project__title", "-allocated_date")

    if q:
        allocations = allocations.filter(
            Q(project__title__icontains=q) |
            Q(material__name__icontains=q)
        )

    # 🔥 GROUP BY PROJECT
    project_allocations = defaultdict(list)

    for a in allocations:
        project_allocations[a.project].append(a)

    context = {
        "project_allocations": dict(project_allocations)
    }

    return render(request, "dashboard/allocation_list.html", context)



def allocate_material(request):
    if request.method == "POST":
        form = MaterialAllocationForm(request.POST)

        if form.is_valid():
            allocation = form.save(commit=False)

            material = allocation.material
            quantity = allocation.quantity

            # 🔴 Prevent over allocation
            if quantity > material.stock.quantity:
                form.add_error('quantity', 'Not enough stock available.')
            else:
                # ✅ Auto assign user
                allocation.allocated_by = request.user

                # ✅ Save allocation
                allocation.save()

                # ✅ Deduct stock
                material.stock.quantity -= quantity
                material.stock.save()

                messages.success(request, "Material allocated successfully.")
                return redirect('allocation_list')

    else:
        form = MaterialAllocationForm()

    return render(request, 'dashboard/allocate_material.html', {'form': form})

def get_material_stock(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    return JsonResponse({
        'stock': material.stock.quantity
    })

def request_material(request):
    MaterialFormSet = modelformset_factory(
        MaterialAllocation,
        form=MaterialAllocationRequestForm,
        extra=1,
        can_delete=True
    )

    if request.method == "POST":
        formset = MaterialFormSet(
            request.POST,
            queryset=MaterialAllocation.objects.none()
        )

        if formset.is_valid():
            for form in formset:
                if not form.cleaned_data:
                    continue
                if form.cleaned_data.get('DELETE'):
                    continue

                project = form.cleaned_data['project']
                material = form.cleaned_data['material']
                quantity = form.cleaned_data['quantity']

                existing = MaterialAllocation.objects.filter(
                    project=project,
                    material=material,
                    allocated_by=request.user.employee,
                    status='pending'
                ).first()

                if existing:
                    # ✅ Merge duplicate requests
                    existing.quantity += quantity
                    existing.save()
                else:
                    allocation = form.save(commit=False)
                    allocation.allocated_by = request.user.employee
                    allocation.save()

            return redirect('my_requests')

    else:
        formset = MaterialFormSet(queryset=MaterialAllocation.objects.none())

    return render(request, "dashboard/request_material.html", {"formset": formset})


def my_requests(request):
    requests = MaterialAllocation.objects.filter(
        allocated_by=request.user.employee
    ).order_by('-id')

    return render(request, "dashboard/my_requests.html", {"requests": requests})



def admin_material_requests(request):
    pending_requests = MaterialAllocation.objects.filter(status='pending').order_by('-id')

    history_list = MaterialAllocation.objects.exclude(status='pending').order_by('-id')

    paginator = Paginator(history_list, 10)  # 10 per page
    page_number = request.GET.get('page')
    history = paginator.get_page(page_number)

    if request.method == "POST":
        req_id = request.POST.get("request_id")
        action = request.POST.get("action")

        req = get_object_or_404(MaterialAllocation, id=req_id)

        admin_user = request.user
        requester = req.allocated_by.user

        if action == "approve":
            try:
                req.approve()

                create_notification(
                    recipient=requester,
                    sender=admin_user,
                    title="Material Request Approved",
                    message=f"{req.material.name} ({req.quantity}) approved for {req.project.title}.",
                    category="material"
                )

                return redirect('admin_material_requests')

            except ValueError as e:
                create_notification(
                    recipient=admin_user,
                    sender=admin_user,
                    title="Approval Failed",
                    message=str(e),
                    category="error"
                )

                # 🔥 stay on same page
                return render(request, "dashboard/admin/material_requests.html", {
                    "pending_requests": pending_requests,
                    "history": history,
                    "error": str(e)
                })

        elif action == "reject":
            req.reject()

            create_notification(
                recipient=requester,
                sender=admin_user,
                title="Material Request Rejected",
                message=f"{req.material.name} ({req.quantity}) rejected for {req.project.title}.",
                category="material"
            )

            return redirect('admin_material_requests')

    return render(request, "dashboard/admin/material_requests.html", {
        "pending_requests": pending_requests,
        "history": history
    })

