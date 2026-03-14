from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import *
from .forms import *


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
    ).order_by("-allocated_date")

    if q:
        allocations = allocations.filter(
            Q(project__name__icontains=q) |
            Q(material__name__icontains=q)
        )

    return render(request, "dashboard/allocation_list.html", {"allocations": allocations})


@login_required(login_url='/users/login')
def allocate_material(request):

    form = MaterialAllocationForm(request.POST or None)

    if form.is_valid():

        form.save()

        messages.success(request, "Material allocated successfully")

        return redirect("allocation_list")

    return render(request, "dashboard/allocate_material.html", {"form": form})



