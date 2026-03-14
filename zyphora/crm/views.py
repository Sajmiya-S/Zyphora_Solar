from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Q
from django.db import transaction


from users.utils import create_notification
from users.views import notify_admins_and_assigned

from .models import *
from .forms import *







# ======================================================
#              USER REVIEW MANAGEMENT
# ======================================================
# This section handles customer/user reviews submitted
# through the website. Admin can view, approve, or delete
# reviews to ensure only appropriate feedback is displayed
# publicly on the website.


@login_required(login_url='/users/login')
def review_list(request):
    review_list = Review.objects.all().order_by('-created_at')
    paginator = Paginator(review_list, 6) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'dashboard/admin/review_list.html', {'page_obj': page_obj})

@login_required(login_url='/users/login')
def approve_review(request, rid):
    review = Review.objects.get(id=rid)
    review.is_approved = True
    review.save()
    admin = CustomUser.objects.get(role='admin')

    create_notification(
        recipient=admin,
        sender=request.user,
        title="Review Approved",
        message=f"Review from {review.name} has been approved",
        link=reverse('review'),
        category="crm"
    )

    return redirect(review_list)


@login_required(login_url='/users/login')
def delete_review(request, rid):
    review = Review.objects.get(id=rid)
    review.delete()

    admin = CustomUser.objects.get(role='admin')

    create_notification(
        recipient=admin,
        sender=request.user,
        title="Review Deleted",
        message=f"Review from {review.name} has been deleted",
        link=reverse('review'),
        category="crm"
    )

    return redirect(review_list)


# ======================================================
# LEAD MANAGEMENT
# ======================================================
# This section manages potential customer leads generated
# from contact forms, service inquiries, or website forms.
# Admin or staff can view, update status, assign, or delete leads.


@login_required(login_url='/users/login')
def lead_list(request):

    status = request.GET.get('status', '')
    query = request.GET.get("q")


    leads = Lead.objects.all()

    if status:
        leads = leads.filter(status=status)

    if query:
        leads = leads.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(assigned_to__username__icontains=query)
        )
        
    leads = leads.order_by('-created_at')

    context = {
        'leads': leads,
        'status_choices': Lead.STATUS_CHOICES,
        'status': status
    }

    return render(request, 'dashboard/admin/lead_list.html', context)


@login_required(login_url='/users/login')
def view_lead(request, lid):
    lead = get_object_or_404(Lead, id=lid)
    return render(request, 'dashboard/admin/view_lead.html', {'lead': lead})


@login_required(login_url='/users/login')
def add_lead(request):
    if request.method == "POST":
        notes = request.POST.get('notes')
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.notes = notes
            lead.save()
            LeadActivity.objects.create(
                lead=lead,
                title="Lead Created",
                description="Lead added manually by admin",
                created_by=request.user
            )
            admin = CustomUser.objects.get(role='admin')
            create_notification(
                recipient=admin,
                title="New Lead Added",
                message=f"{lead.name} has been added to CRM",
                link=reverse('view_lead', kwargs={'lid': lead.id})
            )
            return redirect(lead_list)
    else: 
        form = LeadForm()
    return render(request,'dashboard/admin/add_lead.html',{'form':form})


@login_required(login_url='/users/login')
def delete_lead(request, lid):
    lead = get_object_or_404(Lead, id=lid)
    lead.delete()

    create_notification(
        recipient=request.user,
        sender=request.user,
        title="Lead Deleted",
        message=f"{lead.name} has been removed from CRM",
        link=reverse('lead_list'),
        category="crm"
    )
    return redirect(lead_list)  


@login_required(login_url='/users/login')
def update_lead(request, lid):

    lead = get_object_or_404(Lead, id=lid)
    activities = lead.activities.all().order_by('-created_at')
    link = reverse('view_lead', kwargs={'lid': lead.id})

    if request.method == "POST":

        old_status = lead.status
        old_priority = lead.priority
        old_followup = lead.follow_up_date
        old_assigned = lead.assigned_to

        form = LeadUpdateForm(request.POST, instance=lead)

        if form.is_valid():

            with transaction.atomic():

                lead = form.save()

                # STATUS CHANGE
                if old_status != lead.status:

                    LeadActivity.objects.create(
                        lead=lead,
                        title="Status Updated",
                        description=f"Status changed to {lead.get_status_display()}",
                        created_by=request.user
                    )

                    notify_admins_and_assigned(
                        sender=request.user,
                        instance=lead,
                        title="Lead Status Updated",
                        message=f"{lead.name} status changed to {lead.get_status_display()}",
                        link=link,
                        admin_cat="crm",
                        emp_cat="lead"
                    )

                # PRIORITY CHANGE
                if old_priority != lead.priority:

                    LeadActivity.objects.create(
                        lead=lead,
                        title="Priority Updated",
                        description=f"Priority changed to {lead.get_priority_display()}",
                        created_by=request.user
                    )

                    if lead.priority == "high":

                        notify_admins_and_assigned(
                            sender=request.user,
                            instance=lead,
                            title="High Priority Lead",
                            message=f"{lead.name} marked HIGH priority",
                            link=link,
                            admin_cat="crm",
                            emp_cat="lead"
                        )

                # ASSIGNMENT CHANGE
                if old_assigned != lead.assigned_to:

                    assigned_name = (
                        lead.assigned_to.username
                        if lead.assigned_to
                        else "Unassigned"
                    )

                    LeadActivity.objects.create(
                        lead=lead,
                        title="Lead Assigned",
                        description=f"Assigned to {assigned_name}",
                        created_by=request.user
                    )

                    notify_admins_and_assigned(
                        sender=request.user,
                        instance=lead,
                        title="Lead Assigned",
                        message=f"{lead.name} has been assigned to {assigned_name}",  
                        link=link,
                        admin_cat="crm",
                        emp_cat="lead"
                    )

                # FOLLOW-UP CHANGE
                if old_followup != lead.follow_up_date and lead.follow_up_date:

                    followup_date = lead.follow_up_date.strftime('%d %b %Y')

                    LeadActivity.objects.create(
                        lead=lead,
                        title="Follow-up Scheduled",
                        description=f"Follow-up scheduled for {followup_date}",
                        created_by=request.user
                    )

                    notify_admins_and_assigned(
                        sender=request.user,
                        instance=lead,
                        title="Follow-up Scheduled",
                        message=f"Follow-up scheduled for {lead.name} on {followup_date}",
                        link=link,
                        admin_cat="crm",
                        emp_cat="lead"
                    )

            return redirect('view_lead', lid=lead.id)

    else:
        form = LeadUpdateForm(instance=lead)

    context = {
        "lead": lead,
        "form": form,
        "activities": activities
    }

    return render(request, 'dashboard/admin/update_lead.html', context)



@login_required(login_url='/users/login')
def mark_followup_done(request, lid):
    lead = get_object_or_404(Lead, id=lid)
    lead.mark_followup_done()
    return redirect(update_lead, lead.id)


@login_required(login_url='/users/login')
def mark_site_visit_done(request, lid):
    lead = get_object_or_404(Lead, id=lid)
    lead.mark_site_visit_done()
    return redirect(update_lead, lead.id)