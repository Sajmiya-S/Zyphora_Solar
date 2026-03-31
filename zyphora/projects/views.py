from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from datetime import datetime,date
from django.http import JsonResponse
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.views.decorators.http import require_POST


from .models import *
from .forms import *


from users.views import notify_admins_and_assigned

from procurement.models import *

from finance.models import *


from crm.models import *








# ======================================================
#               PROJECT MANAGEMENT 
# ======================================================
# Handles project listing, updating, viewing, activities,
# gallery management, and progress tracking.

@login_required(login_url='/users/login')
def all_projects(request):
    status = request.GET.get('status', '')
    query = request.GET.get("q")
    projects = Project.objects.all()

    # If engineer, filter projects assigned to them
    if request.user.role == "engineer":
        employee = Employee.objects.filter(user=request.user).first()
        if employee:
            projects = projects.filter(engineer=employee)

    if request.user.role == "liaison":
        employee = Employee.objects.filter(user=request.user).first()
        if employee:
            projects = projects.filter(status__in =['structure','electrical','liasoning','energisation','completed'])

    if request.user.role == 'staff':
        employee = Employee.objects.filter(user=request.user).first()
        if employee:
            projects = Project.objects.filter(installation_tasks__assigned_to=request.user).distinct()

    # Filter by status
    if status:
        projects = projects.filter(status=status)

    # Search
    if query:
        projects = projects.filter(
            Q(title__icontains=query) |
            Q(project_type__icontains=query) |
            Q(engineer__user__username__icontains=query)
        )

    projects = projects.order_by('-created_at')

    # PAGINATION
    paginator = Paginator(projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'projects': page_obj.object_list,  
        'page_obj': page_obj,              
        'status_choices': Project.STATUS_CHOICES,
        'status': status
    }

    return render(request, 'dashboard/all_projects.html', context)


@login_required(login_url='/users/login')
def completed_projects(request):
    projects = Project.objects.filter(status='completed')

    if request.user.role == 'engineer':
        projects = projects.filter(engineer=request.user)
    if request.user.role == 'liaison':
        projects = projects.filter(licensing__assigned_to=request.user)
    if request.user.role == 'staff':
        projects = projects.filter(installation_tasks__assigned_to=request.user)

    projects = projects.distinct()

    return render(request,'dashboard/completed_projects.html',{'projects':projects})

@login_required(login_url='/users/login')
def completed_project_detail(request,pid):
    project = Project.objects.get(id=pid)
    return render(request,'dashboard/completed_project_detail.html',{'project':project})

@login_required(login_url='/users/login')
def update_project(request, pid):
    project = get_object_or_404(Project, id=pid)
    link = reverse('project_detail', kwargs={'pid': project.id})

    status_order = [status[0] for status in Project.STATUS_CHOICES]
    track_fields = ["engineer", "description", "revenue", "location"]

    def get_display_value(value):
        if hasattr(value, 'name'):
            return value.name
        if hasattr(value, 'user'):
            return value.user.username
        return str(value) if value else None

    def format_currency(value):
        return f"₹{value:,.2f}" if value else None

    def format_date(value):
        return value.strftime("%d %b %Y") if value else None

    def log_field_change(field_name, old_value, new_value):
        if old_value != new_value:

            if not old_value and new_value:
                title = f"{field_name} Added"
                message = f"{field_name} set to {new_value}"
            elif old_value and not new_value:
                title = f"{field_name} Removed"
                message = f"{field_name} was removed"
            else:
                title = f"{field_name} Updated"
                message = f"{field_name} changed from {old_value} to {new_value}"

            ProjectActivity.objects.create(
                project=project,
                title=title,
                description=message,
                created_by=request.user,
            )

    if request.method == "POST":

        old_data = {}
        for field in track_fields:
            value = getattr(project, field)
            old_data[field] = format_currency(value) if field == "revenue" else get_display_value(value)

        old_start = format_date(project.start_date)
        old_end = format_date(project.end_date)

        form = ProjectForm(request.POST, request.FILES, instance=project)

        if form.is_valid():
            with transaction.atomic():

                engineer = form.cleaned_data.get("engineer")
                if engineer and isinstance(engineer, CustomUser):
                    engineer = Employee.objects.filter(user=engineer).first()

                project = form.save(commit=False)
                project.engineer = engineer
                project.save()

                new_data = {}
                for field in track_fields:
                    value = getattr(project, field)
                    new_data[field] = format_currency(value) if field == "revenue" else get_display_value(value)

                for field in track_fields:
                    log_field_change(field.replace("_", " ").title(), old_data[field], new_data[field])

                log_field_change("Start Date", old_start, format_date(project.start_date))
                log_field_change("End Date", old_end, format_date(project.end_date))

                # FILE UPLOAD
                valid_categories = [c[0] for c in ProjectMedia.CATEGORY_CHOICES]
                category = request.POST.get('category')
                if category not in valid_categories:
                    category = 'installation_photo'

                files = request.FILES.getlist('files')
                captions = request.POST.getlist('captions') or []

                uploaded_count = 0
                for i, f in enumerate(files):
                    caption = captions[i] if i < len(captions) else ""

                    ProjectMedia.objects.create(
                        project=project,
                        uploaded_by=request.user,
                        file=f,
                        caption=caption,
                        category=category
                    )
                    uploaded_count += 1

                if uploaded_count:
                    title = "Project Media Added"
                    message = f"{uploaded_count} file(s) uploaded to {project.title}"

                    ProjectActivity.objects.create(
                        project=project,
                        title=title,
                        description=message,
                        created_by=request.user
                    )

                    notify_admins_and_assigned(
                        sender=request.user,
                        instance=project,
                        title=title,
                        message=message,
                        link=link,
                        admin_cat="project",
                        emp_cat="project"
                    )

            return redirect('project_detail', pid=pid)

    else:
        form = ProjectForm(instance=project)

    context = {
        "project": project,
        "form": form,
        "media_files": project.media.all(),
        "status_order": status_order,
        "progress_percent": project.progress_percent,
        "today": date.today().isoformat(),
    }

    return render(request, "dashboard/edit_project.html", context)


@login_required(login_url='/users/login')
def view_project(request,pid):
    project = Project.objects.get(id=pid)
    activities = project.activities.order_by('-created_at') 

    context = {
        'project':project,
        'activities':activities,
        'progress': project.progress_percent,
        'completed_stages': project.completed_stages,
    }

    return render(request, 'dashboard/view_project.html', context)



@login_required(login_url='/users/login')
def project_activities(request, pid):
    project = get_object_or_404(Project, pk=pid)
    activities = ProjectActivity.objects.filter(project=project).order_by('-created_at')  

    context = {
        'project': project,
        'activities': activities
    }

    return render(request, 'dashboard/activities.html', context)





@login_required(login_url='/users/login')
def recent_activity(request):

    activities = ProjectActivity.objects.select_related(
        'project', 'created_by'
    ).order_by('-created_at')

    paginator = Paginator(activities, 10)
    page = request.GET.get('page')
    activities_page = paginator.get_page(page)

    today = timezone.now().date()
    yesterday = today - timedelta(days=1)

    grouped = {
        "today": [],
        "yesterday": [],
        "older": []
    }

    for activity in activities_page:
        activity_date = activity.created_at.date()

        if activity_date == today:
            grouped["today"].append(activity)
        elif activity_date == yesterday:
            grouped["yesterday"].append(activity)
        else:
            grouped["older"].append(activity)

    context = {
        "activities": activities_page,
        "grouped_activities": grouped
    }

    return render(request, 'dashboard/recent_activity.html', context)



@login_required(login_url='/users/login')
def add_activity(request,pid):

    project = get_object_or_404(Project,id=pid)

    if request.method == "POST":

        form = ProjectActivityForm(request.POST)

        if form.is_valid():

            activity = form.save(commit=False)
            activity.project = project
            activity.created_by = request.user
            activity.save()

            notify_admins_and_assigned(
                sender=request.user,
                instance=project,
                title=activity.title,
                message=activity.description or "New activity added to project",
                link = reverse('project_detail',kwargs={'pid':project.id}),
                admin_cat="projects",
                emp_cat="projects"
            )

            return redirect('project_detail',project.id)

    else:
        form = ProjectActivityForm()

    context = {
        'project':project,
        'form':form
    }

    return render(request,'dashboard/add_activity.html',context)



@login_required(login_url='/users/login')
def gallery_projects(request):
    projects = Project.objects.all()
    return render(request,'dashboard/gallery_projects.html',{'projects':projects})


@login_required(login_url='/users/login')
def add_project_media(request, pid):
    project = get_object_or_404(Project, id=pid)

    if request.method == "POST":
        files = request.FILES.getlist('files')  
        captions = request.POST.getlist('captions')  
        category = request.POST.get('category', 'installation_photo')  

        uploaded_count = 0

        for i, f in enumerate(files):
            caption = captions[i] if i < len(captions) else ""
            ProjectMedia.objects.create(
                project=project,
                uploaded_by=request.user,
                file=f,
                caption=caption,
                category=category
            )
            uploaded_count += 1

        if uploaded_count:
            title = "Project Media Added"
            message = f"{uploaded_count} files uploaded to {project.title}"

            ProjectActivity.objects.create(
                project=project,
                title=title,
                description=message,
                created_by=request.user
            )

            notify_admins_and_assigned(
                sender=request.user,
                instance=project,
                title=title,
                message=message,
                link=reverse('project_gallery', kwargs={'pid': project.id}),
                admin_cat="project",
                emp_cat="project"
            )

        return redirect(request.META.get("HTTP_REFERER"))

    return redirect('project_gallery', pid=pid)


@login_required(login_url='/users/login')
def delete_project_media(request, id):
    media = get_object_or_404(ProjectMedia, id=id)
    pid = media.project.id
    media.delete()
    return redirect('project_gallery', pid=pid)

@login_required(login_url='/users/login')
def update_caption(request, id):
    # Get the media object
    media = get_object_or_404(ProjectMedia, id=id)
    pid = media.project.id

    if request.method == "POST":
        # Only update caption and file (if replaced)
        caption = request.POST.get("caption", media.caption)
        file = request.FILES.get("file", None)

        media.caption = caption
        if file:
            media.file = file
        media.save()

        return redirect('project_gallery', pid=pid)

    return redirect('project_gallery', pid=pid)


@login_required(login_url='/users/login')
def project_gallery(request, pid):

    project = Project.objects.get(id=pid)
    files = project.media.all()
    context = {
            'project': project,
            'files': files
        }

    return render(request,'dashboard/project_gallery.html',context)



@login_required(login_url='/users/login')
def assigned_tasks(request):
    # Only supervisors allowed
    if request.user.role not in ['admin', 'engineer']:
        return redirect('my_tasks')

    tasks = Task.objects.filter(assigned_by=request.user).order_by('-created_at')

    return render(request, "dashboard/assigned_tasks.html", {'tasks':tasks})

@login_required(login_url='/users/login')
def my_tasks(request):
    user = request.user
    today = timezone.now().date()

    # Get tasks assigned to logged-in user
    tasks = Task.objects.filter(assigned_to=user)

    # Count tasks for badge display
    task_count = tasks.filter(status__in=['new', 'in_progress']).count()

    # Optional: Filter by GET param (today, pending, completed, overdue)
    filter_type = request.GET.get('filter')
    if filter_type == 'today':
        tasks = tasks.filter(due_date=today)
    elif filter_type == 'pending':
        tasks = tasks.exclude(status='completed')
    elif filter_type == 'overdue':
        tasks = tasks.exclude(status='completed').filter(due_date__lt=today)
    elif filter_type == 'completed':
        tasks = tasks.filter(status='completed')

    context = {
        "tasks": tasks,
        "task_count": task_count,
        "today": today,
        "filter_type": filter_type or "all",
    }
    return render(request, "dashboard/tasks.html", context)

@login_required(login_url='/users/login')
def create_task(request):

    if request.method == "POST":

        form = TaskForm(request.POST, user=request.user)

        # Hide assignment fields for normal users
        if request.user.role not in ['admin', 'engineer']:
            form.fields.pop('assigned_to', None)

        if form.is_valid():
            task = form.save(commit=False)

            # assign automatically to self
            if request.user.role not in ['admin', 'engineer']:
                task.assigned_to = request.user

            task.assigned_by = request.user

            task.save()

            if request.user.role in ['admin', 'engineer']:
                return redirect('assigned_tasks')
            else:
                return redirect('my_tasks')

    else:
        form = TaskForm(user=request.user)

        if request.user.role not in ['admin', 'engineer']:
            form.fields.pop('assigned_to', None)

    return render(request, "dashboard/create_task.html", {"form": form})

    


@login_required(login_url='/users/login')
def complete_task(request, id):
    task = get_object_or_404(Task, id=id)
    if task.status != 'completed':
        task.status = 'completed'
        task.save()

        # =====================================
        # ✅ FOLLOW-UP TASK
        # =====================================
        if 'follow' in task.title.lower():

            followup = FollowUp.objects.filter(
                status='pending'
            ).order_by('scheduled_date').first()

            if followup:
                followup.mark_done(user=request.user, note="Completed via task")

                # 🟢 Activity Log
                LeadActivity.objects.create(
                    lead=followup.lead,
                    title="Follow-up Completed",
                    description=f"Follow-up on {followup.scheduled_date} marked as done via task '{task.title}'",
                    created_by=request.user
                )

        # =====================================
        # ✅ SITE VISIT TASK
        # =====================================
        elif 'site' in task.title.lower():

            visit = SiteVisit.objects.filter(
                status='pending'
            ).order_by('scheduled_date').first()

            if visit:
                visit.mark_done(user=request.user, note="Completed via task")

                # 🟢 Activity Log
                LeadActivity.objects.create(
                    lead=visit.lead,
                    title="Site Visit Completed",
                    description=f"Site visit on {visit.scheduled_date} completed via task '{task.title}'",
                    created_by=request.user
                )
    return redirect('my_tasks')


@login_required(login_url='/users/login')
def delete_task(request, id):
    task = get_object_or_404(Task, id=id)
    task.delete()
    if request.user.role in ['admin', 'engineer']:
        return redirect(assigned_tasks)
    else:
        return redirect(my_tasks)



@login_required(login_url='/users/login')
def edit_task(request, id):

    task = get_object_or_404(Task, id=id)

    # Permission check
    if not (
        request.user == task.assigned_to
        or request.user.role in ['admin', 'engineer']
    ):
        return redirect('my_tasks')

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task, user=request.user)

        if form.is_valid():
            task = form.save(commit=False)

            # Ensure assigned_to if hidden
            if not task.assigned_to:
                task.assigned_to = request.user

            task.assigned_by = request.user

            task.save()

            if request.user.role in ['admin', 'engineer']:
                return redirect(assigned_tasks)
            else:
                return redirect(my_tasks)

    else:
        form = TaskForm(instance=task, user=request.user)

    return render(request, "dashboard/edit_task.html", {
        "form": form,
        "task": task
    })


@login_required(login_url='/users/login')
def feasibility_list(request):

    # Admin view
    if request.user.role == "admin":
        projects = Project.objects.exclude(status='completed')
        reports = FeasibilityReport.objects.select_related("project", "submitted_by")
    
    # Engineer view
    elif request.user.role == "engineer":
        try:
            engineer = Employee.objects.get(user=request.user)
        except Employee.DoesNotExist:
            # If engineer record is missing
            projects = Project.objects.none()
            reports = FeasibilityReport.objects.none()
        else:
            # Projects assigned to this engineer
            projects = Project.objects.filter(engineer=engineer).exclude(status='completed')
            # All reports for these projects
            reports = FeasibilityReport.objects.filter(project__in=projects).select_related("project", "submitted_by")
    
    # Other roles (if any)
    else:
        projects = Project.objects.none()
        reports = FeasibilityReport.objects.none()

    # Categorize
    pending_projects = projects.filter(status='feasibility').exclude(
        id__in=reports.values_list('project_id', flat=True)
    )
    submitted_reports = reports.filter(is_approved=False)
    approved_reports = reports.filter(is_approved=True)

    context = {
        'pending_projects': pending_projects,
        'submitted_reports': submitted_reports,
        'approved_reports': approved_reports,
    }

    return render(request, 'dashboard/engineer/feasibility_list.html', context)



@login_required(login_url='/users/login')
def create_feasibility_general(request):

    user = request.user
    engineer = Employee.objects.filter(user=user).first()

    # Filter projects in feasibility stage
    if user.role == "admin":
        projects = Project.objects.filter(status='feasibility')
    else:
        projects = Project.objects.filter(engineer=engineer, status='feasibility')

    if request.method == "POST":
        project_id = request.POST.get("project")

        report = FeasibilityReport.objects.create(
            project_id=project_id,
            site_type=request.POST.get("site_type"),
            roof_type=request.POST.get("roof_type"),
            roof_area=request.POST.get("roof_area"),
            shadow_analysis=request.POST.get("shadow_analysis"),
            orientation=request.POST.get("orientation"),
            connection_type=request.POST.get("connection_type"),
            monthly_consumption=request.POST.get("monthly_consumption"),
            suggested_capacity=request.POST.get("suggested_capacity"),
            system_type=request.POST.get("system_type"),
            remarks=request.POST.get("remarks"),
            submitted_by=engineer
        )

        return redirect('feasibility_list')

    return render(request, 'dashboard/engineer/create_feasibility_general.html', {
        'projects': projects
    })



@login_required(login_url='/users/login')
def create_feasibility(request, pid):

    project = get_object_or_404(Project, id=pid)

    engineer = Employee.objects.filter(user=request.user).first()

    # Prevent duplicate feasibility
    if hasattr(project, 'feasibility'):
        return redirect('feasibility_list')

    if request.method == "POST":
        FeasibilityReport.objects.create(
            project=project,
            site_type=request.POST.get("site_type"),
            roof_type=request.POST.get("roof_type"),
            roof_area=request.POST.get("roof_area"),
            shadow_analysis=request.POST.get("shadow_analysis"),
            orientation=request.POST.get("orientation"),
            connection_type=request.POST.get("connection_type"),
            monthly_consumption=request.POST.get("monthly_consumption"),
            suggested_capacity=request.POST.get("suggested_capacity"),
            system_type=request.POST.get("system_type"),
            remarks=request.POST.get("remarks"),
            submitted_by=request.user
        )

        return redirect('feasibility_list')

    return render(request, 'dashboard/engineer/create_feasibility.html', {'project': project})



@login_required(login_url='/users/login')
def feasibility_detail(request, fid):

    report = get_object_or_404(
        FeasibilityReport.objects.select_related("project", "submitted_by"),
        id=fid
    )

    return render(request, 'dashboard/engineer/feasibility_detail.html', {
        'report': report,
        'project': report.project,
        'client': report.project.lead
    })




@login_required(login_url='/users/login')
def approve_feasibility(request, fid):

    report = get_object_or_404(FeasibilityReport, id=fid)

    # Approve report
    report.is_approved = True
    report.save()

    # 🔥 AUTO MOVE PROJECT TO DESIGN PHASE
    project = report.project
    project.status = 'design_prep'
    project.save()

    return redirect('feasibility_detail', fid=report.id)

@login_required(login_url='/users/login')
def reject_feasibility(request, fid):
    report = get_object_or_404(FeasibilityReport, id=fid)
    if request.method == "POST":
        report.is_approved = False
        report.approval_notes = request.POST.get("notes")
        report.save()
    return redirect('feasibility_detail', fid=report.id)



@login_required(login_url='/users/login')
def design_list(request):
    query = request.GET.get('q')

    if request.user.role == "admin":
        projects = Project.objects.all()
    else:
        engineer = Employee.objects.filter(user=request.user).first()
        projects = Project.objects.filter(engineer=engineer) if engineer else Project.objects.none()

    projects = projects.exclude(status='completed')

    if query:
        projects = projects.filter(
            Q(title__icontains=query) |
            Q(location__icontains=query) |
            Q(project_type__icontains=query) |
            Q(status__icontains=query) |
            Q(lead__name__icontains=query) |
            Q(lead__phone__icontains=query) |
            Q(lead__location__icontains=query) |
            Q(lead__service__icontains=query)
        )

    projects = projects.select_related('lead', 'engineer') \
                       .prefetch_related('design_documents', 'lead__followups')

    projects_with_phase = []

    for project in projects:
        docs = project.design_documents.all()

        # Match design_detail phase logic
        if not docs.exists():
            phase = "preparation"
            correction_required = False
        elif docs.filter(needs_correction=True).exists():
            phase = "correction"
            correction_required = True
        elif docs.filter(approved=False).exists():
            phase = "discussion"
            correction_required = False
        elif not hasattr(project, 'design_costing'):
            phase = "design_costing"
            correction_required = False
        elif hasattr(project, 'design_costing') and project.design_costing.status == "pending":
            phase = "design_costing_review"
            correction_required = False
        elif hasattr(project, 'design_costing') and project.design_costing.status == "approved" and not hasattr(project, 'project_costing'):
            phase = "project_costing"
            correction_required = False
        elif hasattr(project, 'project_costing'):
            phase = "completed"
            correction_required = False
        else:
            phase = "project_costing"
            correction_required = False

        projects_with_phase.append({
            "project": project,
            "phase": phase,
            "correction_required": correction_required
        })

    return render(request, "dashboard/design_list.html", {
        "projects_with_phase": projects_with_phase
    })


@login_required(login_url='/users/login')
def design_detail(request, pid):

    project = get_object_or_404(Project, id=pid)
    docs = project.design_documents.all().order_by('uploaded_at')

    design_costing = getattr(project, "design_costing", None)
    project_costing = getattr(project, "project_costing", None)

    if request.method == "POST" and "notify_engineer" in request.POST:
        message = f"Please upload the design for project '{project.title}'."
        create_notification(
            sender=request.user,
            recipient=project.engineer.user,
            title="Message from Admin",
            message=message,
            category="admin",
            link=reverse('design_detail',kwargs={'pid':project.id})
        )
        messages.success(request, "Notification sent to engineer!")

    # =========================================================
    # 🔷 PHASE LOGIC
    # =========================================================
    if not docs.exists():
        current_phase = "preparation"

    elif docs.filter(needs_correction=True).exists():
        current_phase = "correction"

    elif docs.filter(discussion_date__isnull=True).exists():
        current_phase = "preparation"

    elif docs.filter(approved=False).exists():
        current_phase = "discussion"

    elif not design_costing:
        current_phase = "design_costing"

    elif design_costing.status == "pending":
        current_phase = "design_costing_review"

    elif project_costing and project_costing.proposal_sent and not project_costing.client_approved:
        current_phase = "client_approval"  # ✅ check this BEFORE project_costing

    elif design_costing.status == "approved" and project_costing and (project_costing.system_costing is not None):
        current_phase = "project_costing"

    else:
        current_phase = "project_costing"

    # =========================================================
    # 🔷 AUTO SAVE APPROVED DOCS
    # =========================================================
    approved_docs = docs.filter(approved=True)

    for doc in approved_docs:
        if not ProjectMedia.objects.filter(
            project=project,
            file=doc.file,
            category='design_document'
        ).exists():

            ProjectMedia.objects.create(
                project=project,
                uploaded_by=doc.uploaded_by,
                file=doc.file,
                caption=doc.caption,
                category='design_document'
            )

    # =========================================================
    # 🔷 POST HANDLING
    # =========================================================
    if request.method == "POST":

        # ================= ENGINEER =================
        if request.user.role == "engineer":

            # 🔵 PREPARATION / CORRECTION
            if current_phase in ["preparation", "correction"]:

                files = request.FILES.getlist("design_files[]")   
                captions = request.POST.getlist("captions[]")     
                date_input = request.POST.get("discussion_date")

                discussion_date = None
                if date_input:
                    try:
                        discussion_date = datetime.strptime(date_input, "%Y-%m-%d").date()
                    except ValueError:
                        discussion_date = None

                docs.update(needs_correction=False)

                for file, caption in zip(files, captions):
                    ProjectDesignDocument.objects.create(
                        project=project,
                        file=file,
                        caption=caption or "",
                        uploaded_by=request.user,
                        discussion_date=discussion_date
                    )

            # 🔷 DESIGN COST
            elif current_phase == "design_costing":

                cost = Decimal(request.POST.get("cost") or 0)
                file = request.FILES.get("design_file")

                DesignCosting.objects.update_or_create(
                    project=project,
                    defaults={
                        "cost": cost,
                        "design_file": file,
                        "entered_by": request.user,
                        "status": "pending"
                    }
                )

        # ================= ADMIN =================
        elif request.user.role == "admin":
            if current_phase in ["preparation", "correction"]:

                date_input = request.POST.get("discussion_date")

                if date_input:
                    try:
                        date_obj = datetime.strptime(date_input, "%Y-%m-%d").date()

                        docs.filter(discussion_date__isnull=True).update(
                            discussion_date=date_obj
                        )

                    except ValueError:
                        pass
            elif current_phase == "discussion":

                action = request.POST.get("action")
                notes = request.POST.get("notes")

                docs.update(notes=notes)

                if action == "approve":
                    docs.update(approved=True, needs_correction=False)
                    project.status = 'design_approval'
                    project.save()

                elif action == "reject":
                    docs.update(needs_correction=True, approved=False)

            elif current_phase == "design_costing_review":

                action = request.POST.get("action")

                if action == "approve":
                    design_costing.status = "approved"
                    design_costing.save()
                    project.status = 'design_costing'
                    project.save()

                elif action == "reject":
                    design_costing.delete()

            elif current_phase == "project_costing":

                if "submit_cost" in request.POST:

                    system_cost = Decimal(request.POST.get("system_cost") or 0)
                    kseb_cost = Decimal(request.POST.get("kseb_cost") or 0)

                    ProjectCosting.objects.update_or_create(
                        project=project,
                        defaults={
                            "design_costing": design_costing,
                            "system_costing": system_cost,
                            "kseb_cost": kseb_cost,
                            "entered_by": request.user,
                            "proposal_sent": False
                        }
                    )

                elif "send_proposal" in request.POST and project_costing:

                    project_costing.proposal_sent = True
                    project_costing.save()
                    project.status = 'costing_approval'
                    project.save()

            elif current_phase == "client_approval":
                print('approval')
                if "client_approve" in request.POST:

                    start_date = request.POST.get("start_date")

                    project_costing.client_approved = True
                    project_costing.approved_at = timezone.now()
                    project_costing.save()

                    project.start_date = start_date
                    project.status = "structure"
                    project.save()

                    for step, _ in InstallationTask.INSTALLATION_STEP_CHOICES:
                        InstallationTask.objects.create(
                            project=project,
                            step=step,
                            status='new',         
                            assigned_to=None      
                        )

                    for step, _ in LicensingTask.LICENSE_STEP_CHOICES:
                        LicensingTask.objects.get_or_create(
                            project=project,
                            step=step,
                            defaults={
                                'status': 'new',       
                                'assigned_to': CustomUser.objects.filter(role='liaison').first()    
                            }
                        )
                    

        return redirect('design_detail', pid=pid)

    # =========================================================
    engineer_can_install = bool(project_costing and project_costing.client_approved)

    template = "dashboard/admin/design_detail_admin.html" if request.user.role == "admin" \
        else "dashboard/engineer/design_detail_engineer.html"

    today = date.today()
    
    return render(request, template, {
        "project": project,
        "design_documents": docs,
        "first_doc" : docs.first(),
        "current_phase": current_phase,
        "today": today,
        "engineer_can_install": engineer_can_install
    })



@login_required(login_url='/users/login')
def delete_design_file(request, doc_id):
    doc = get_object_or_404(ProjectDesignDocument, id=doc_id)
    project_id = doc.project.id

    # Permission check
    if request.user != doc.uploaded_by and request.user.role != "admin":
        return redirect('design_detail', pid=project_id)

    # Allow delete only in correction phase
    if not doc.project.design_documents.filter(needs_correction=True).exists():
        return redirect('design_detail', pid=project_id)

    doc.delete()

    return redirect('design_detail', pid=project_id)



@login_required(login_url='/users/login')
def installation_progress(request):
    engineer = Employee.objects.filter(user=request.user).first()
    search = request.GET.get('q', '')

    # Base projects in structure/electrical
    projects = Project.objects.filter(status__in=['structure', 'electrical'])

    # Engineer sees only their projects
    if engineer and request.user.role == 'engineer':
        projects = projects.filter(engineer=engineer)

    # Staff users for assignment dropdown
    staff_users = CustomUser.objects.filter(role='staff')

    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        # 1️⃣ Assign task
        if form_type == 'assign_task':
            task_id = request.POST.get('task_id')
            assigned_to_id = request.POST.get('assigned_to')
            if task_id:
                task = InstallationTask.objects.filter(id=task_id).first()
                if task:
                    task.assigned_to = CustomUser.objects.filter(id=assigned_to_id).first() if assigned_to_id else None
                    task.notes = (task.notes or '') + f'\nAssigned by {request.user}'
                    task.save()
                    if task.assigned_to:
                        create_notification(
                            recipient=task.assigned_to,
                            title=f'Installation task {task.step} assigned for {task.project.title}',
                            message=f'You have been assigned the installation task: {task.step} for project {task.project.title}.',
                            sender=request.user,
                            link=reverse('update_work_progress')
                        )
            return redirect('installation_progress')

        # 2️⃣ Mark task completed
        elif form_type == 'mark_task_completed':
            complete_task_id = request.POST.get('complete_task_id')
            task = InstallationTask.objects.filter(id=complete_task_id).first()
            if task and task.status != 'completed':
                task.status = 'completed'
                task.notes = (task.notes or '') + f'\nMarked completed by {request.user}'
                task.save()
                if task.assigned_to:
                    create_notification(
                        recipient=task.assigned_to,
                        title=f'Task {task.step} marked completed',
                        message=f'Task "{task.step}" in project "{task.project.title}" has been marked completed by {request.user}.',
                        sender=request.user,
                        link=reverse('update_work_progress')
                    )
            return redirect('installation_progress')

        # 3️⃣ Update project status
        elif form_type == 'update_project_status':
            project_id = request.POST.get('project_id')
            status = request.POST.get('status')
            project = Project.objects.filter(id=project_id).first()
            if project and status and status != project.status:
                project.status = status
                project.save()
            return redirect('installation_progress')

    # Prepare filtered tasks and progress
    for project in projects:
        tasks = project.installation_steps()
        if request.user.role == 'staff':
            tasks = [t for t in tasks if t.assigned_to == request.user]
        if search:
            tasks = [t for t in tasks if search.lower() in t.get_step_display().lower() or 
                     (t.notes and search.lower() in t.notes.lower()) or 
                     search.lower() in project.title.lower()]
        project.filtered_tasks = tasks
        project.real_progress = InstallationTask.project_progress(project)

    return render(request, "dashboard/installation_progress.html", {
        "projects": projects,
        "search": search,
        "staff_users": staff_users,
    })


# List of service requests assigned to the logged-in engineer
@login_required(login_url='/users/login')
def assigned_service_requests(request):
    employee = get_object_or_404(Employee, user=request.user)
    service_requests = ServiceRequest.objects.filter(assigned_to=employee).order_by('-created_at')
    return render(request, 'dashboard/service_requests.html', {'service_requests': service_requests})





@login_required(login_url='/users/login')
def service_history(request):

    employee = get_object_or_404(Employee, user=request.user)
    
    service_requests = ServiceRequest.objects.filter(
        assigned_to=employee
    ).order_by('-created_at')  # newest first

    return render(request, 'dashboard/service_history.html', {
        'service_requests': service_requests
    })


@login_required(login_url='/users/login')
def add_service_report(request,rid):
    service_request = get_object_or_404(
        ServiceRequest, id=rid, assigned_to__user=request.user
    )

    # Prevent adding a report if one already exists
    if hasattr(service_request, 'report'):
        return redirect('service_report_detail', service_request_id=service_request.id)

    if request.method == "POST":
        form = ServiceReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the report
            report = form.save(commit=False)
            report.service_request = service_request
            report.report_by = request.user.employee
            report.save()

            # Mark the service request as completed
            service_request.status = 'completed'
            service_request.save()

            return redirect('assigned_service_requests')  # back to list
    else:
        form = ServiceReportForm()

    return render(request, 'dashboard/engineer/add_service_report.html', {
        'form': form,
        'service_request': service_request
    })


@login_required(login_url='/users/login')
def service_requests(request):
    """View for salesperson to see all service requests related to their leads/projects."""

    # Get all service requests for projects where the salesperson is handling the lead
    all_requests = ServiceRequest.objects.filter(
        project__lead__assigned_to=request.user
    ).select_related('project', 'requested_by', 'assigned_to')

    context = {
        'pending_requests': all_requests.filter(status='pending'),
        'in_progress_requests': all_requests.filter(status='in_progress'),
        'completed_requests': all_requests.filter(status='completed'),
        'cancelled_requests': all_requests.filter(status='cancelled'),
        'unassigned_count': all_requests.filter(status='pending', assigned_to__isnull=True).count(),
        'in_progress_count': all_requests.filter(status='in_progress').count(),
        'completed_count': all_requests.filter(status='completed').count(),
        'cancelled_count': all_requests.filter(status='cancelled').count(),
    }

    return render(request, 'dashboard/sales/service_requests.html', context)


@login_required(login_url='/users/login')
def redirect_service_request(request, pk):
    """Assign a service request to an engineer."""
    
    sr = get_object_or_404(ServiceRequest, pk=pk)

    # Get all engineers in the project (you could filter by role)
    engineers = Employee.objects.filter(project=sr.project)
    
    if request.method == 'POST':
        engineer_id = request.POST.get('engineer')
        assigned_engineer = get_object_or_404(Employee, pk=engineer_id)
        sr.assigned_to = assigned_engineer
        sr.status = 'in_progress'
        sr.save()
        return redirect('service_requests')
    
    return render(request, 'dashboard/sales/redirect_service_request.html', {
        'sr': sr,
        'engineers': engineers
    })

@login_required(login_url='/users/login')
def add_service_request(request):
    # Only show projects assigned to this salesperson
    form = ServiceRequestForm()
    form.fields['project'].queryset = Lead.objects.filter(assigned_to=request.user,status='converted')
    form.fields['assigned_to'].queryset = Employee.objects.filter(user__role='engineer')  

    if request.method == 'POST':
        form = ServiceRequestForm(request.POST)
        form.fields['project'].queryset = Project.objects.filter(lead__assigned_to=request.user)
        form.fields['assigned_to'].queryset = Employee.objects.filter(user__role='engineer')
        if form.is_valid():
            sr = form.save(commit=False)
            sr.status = 'pending' if not sr.assigned_to else 'in_progress'
            sr.save()
            
            # Create notifications
            # 1️⃣ Admin notification
            admins = CustomUser.objects.filter(is_superuser=True)
            for admin in admins:
                create_notification(
                    recipient=admin,
                    title=f"New Service Request: {sr.title}",
                    message=f"{request.user.get_full_name()} created a new service request for project '{sr.project.title}'.",
                    sender=request.user,
                    link=f"/service-requests/{sr.pk}/"
                )

            # 2️⃣ Notify the salesperson (request.user)
            create_notification(
                recipient=request.user,
                title=f"Service Request Created: {sr.title}",
                message=f"You created a service request for project '{sr.project.title}'.",
                sender=request.user,
                link=f"/service-requests/{sr.pk}/"
            )

            # 3️⃣ Notify the engineer, if assigned
            if sr.assigned_to:
                create_notification(
                    recipient=sr.assigned_to.user,
                    title=f"New Service Request Assigned: {sr.title}",
                    message=f"A service request has been assigned to you for project '{sr.project.title}'.",
                    sender=request.user,
                    link=f"/service-requests/{sr.pk}/"
                )

            return redirect(service_requests)

    return render(request, 'dashboard/sales/add_request.html', {'form': form})



@login_required(login_url='/users/login')
def service_reports(request):
    reports = ServiceReport.objects.filter(
        service_request__project__lead__assigned_to=request.user
    ).select_related('service_request', 'service_request__project', 'report_by')

    return render(request,'dashboard/sales/service_reports.html',{'reports':reports})

@login_required(login_url='/users/login')
def service_report_detail(request,rid):
    report = ServiceReport.objects.get(id=rid)

    return render(request, 'dashboard/sales/service_report_detail.html', {'report': report})




@login_required(login_url='/users/login')
def installation_tasks(request):

    filter_type = request.GET.get('filter', 'pending')
    today = timezone.now().date()

    base_qs = InstallationTask.objects.filter(
        assigned_to=request.user
    ).select_related('project')

    # 🔥 COUNTS
    counts = {
        "today": base_qs.filter(due_date=today).count(),

        "pending": base_qs.filter(
            Q(status__in=['new', 'in_progress']),
            Q(due_date__gt=today) | Q(due_date__isnull=True)
        ).count(),

        "completed": base_qs.filter(status='completed').count(),

        "overdue": base_qs.filter(
            Q(due_date__lt=today),
            ~Q(status='completed')
        ).count(),
    }

    # 🔥 FILTER LOGIC
    tasks = base_qs

    if filter_type == "today":
        tasks = tasks.filter(due_date=today)

    elif filter_type == "pending":
        tasks = tasks.filter(
            Q(status__in=['new', 'in_progress']),
            Q(due_date__gt=today) | Q(due_date__isnull=True)
        )

    elif filter_type == "completed":
        tasks = tasks.filter(status='completed')

    elif filter_type == "overdue":
        tasks = tasks.filter(
            Q(due_date__lt=today),
            ~Q(status='completed')
        )

    return render(request, "dashboard/staff/installation_tasks.html", {
        "tasks": tasks,
        "filter_type": filter_type,
        "counts": counts,
        "today": today
    })





@login_required(login_url='/users/login')
def update_work_progress(request):

    tasks = InstallationTask.objects.filter(
        assigned_to=request.user
    ).select_related('project').order_by('project', 'created_at')

    project_data = {}

    # Group tasks by project
    for task in tasks:
        project = task.project

        if project not in project_data:
            project_data[project] = []

        project_data[project].append(task)

    # Identify current step
    for project, task_list in project_data.items():
        current_found = False

        for task in task_list:
            if task.status == 'completed':
                task.is_current = False
            elif not current_found:
                task.is_current = True
                current_found = True
            else:
                task.is_current = False

        # 🔥 Attach latest progress to project
        latest = project.progress_snapshots.first()
        project.progress = latest.progress_percent if latest else 0

    # Handle complete action
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        notes = request.POST.get('notes')

        task = get_object_or_404(
            InstallationTask,
            id=task_id,
            assigned_to=request.user
        )

        task.status = 'completed'
        task.notes = notes
        task.completed_at = timezone.now()
        task.save()

        # 🔥 Calculate progress
        project = task.project
        all_tasks = project.installation_tasks.all()

        total = all_tasks.count()
        completed = all_tasks.filter(status='completed').count()

        progress = int((completed / total) * 100) if total > 0 else 0

        # 🔥 Save snapshot (avoid duplicates)
        last = project.progress_snapshots.first()
        if not last or last.progress_percent != progress:
            InstallationProgress.objects.create(
                project=project,
                progress_percent=progress
            )

        # 🔥 Auto-complete project
        if completed == total and total > 0:
            project.status = 'completed'
            project.save(update_user=request.user)
        print("Progress:", progress)
        return redirect('update_work_progress')

    return render(request, 'dashboard/staff/update_work_progress.html', {
        'project_data': project_data
    })



@login_required(login_url='/users/login')
def upload_photos(request):
    if request.method == 'POST':
        form = ProjectMediaForm(request.POST, user=request.user)
        files = request.FILES.getlist('files')  # Multiple files

        if form.is_valid():
            project = form.cleaned_data['project']
            category = form.cleaned_data['category']
            caption = form.cleaned_data.get('caption', '')

            installation_task = form.cleaned_data.get('installation_task') if category == 'installation_photo' else None
            issue = form.cleaned_data.get('issue') if category == 'issue_photo' else None
            work_report = form.cleaned_data.get('work_report')
            service_report = form.cleaned_data.get('service_report')

            if not files:
                messages.error(request, "Please select at least one file to upload.")
            else:
                for f in files:
                    ProjectMedia.objects.create(
                        project=project,
                        uploaded_by=request.user,
                        file=f,
                        category=category,
                        caption=caption,
                        installation_task=installation_task,
                        issue=issue,
                        work_report=work_report,
                        service_report=service_report,
                    )
                messages.success(request, f"{len(files)} file(s) uploaded successfully!")
                return redirect('upload_photos')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ProjectMediaForm(user=request.user)

    return render(request, 'dashboard/staff/upload_photos.html', {'form': form})


@login_required(login_url='/users/login')
def get_project_photos(request):
    project_id = request.GET.get('project_id')

    photos = ProjectMedia.objects.filter(project_id=project_id,category='installation_photo').order_by('-uploaded_at')

    data = []
    for photo in photos:
        data.append({
            'url': photo.image.url,
            'caption': photo.caption or '',
        })

    return JsonResponse({'photos': data})




@login_required(login_url='/users/login')
def report_issues(request):
    form = InstallationIssueForm()

    if request.method == 'POST':
        form = InstallationIssueForm(request.POST, request.FILES)
        if form.is_valid():
            issue = form.save(commit=False)
            issue.reported_by = request.user
            issue.save()
            return redirect('report_issues')

    return render(request, 'dashboard/staff/report_issues.html', {'form': form})



@login_required(login_url='/users/login')
def create_daily_report(request):
    if request.method == 'POST':
        form = WorkReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user  # auto assign user
            report.save()
            return redirect('work_report_list')
    else:
        form = WorkReportForm()

    return render(request, 'dashboard/engineer/create_report.html', {
        'form': form
    })


@login_required(login_url='/users/login')
def daily_report_list(request):

    reports = WorkReport.objects.filter(
        user=request.user,
        report_type='daily'   # ✅ important (only daily reports)
    )

    date = request.GET.get('date')
    status = request.GET.get('status')
    project = request.GET.get('project')

    if date:
        reports = reports.filter(date=date)

    if status:
        reports = reports.filter(status=status)

    if project:
        reports = reports.filter(project_id=project)

    reports = reports.select_related('project').order_by('-date')

    return render(request, 'dashboard/engineer/report_list.html', {
        'reports': reports,
        'filters': {
            'date': date,
            'status': status,
            'project': project,
        }
    })



@login_required(login_url='/users/login')
def daily_report_detail(request, pk):
    report = get_object_or_404(WorkReport, pk=pk)

    return render(request, 'dashboard/engineer/report_detail.html', {
        'report': report
    })


@login_required(login_url='/users/login')
def weekly_report_list(request):
    reports = WorkReport.objects.filter(report_type='weekly').order_by('-date')

    # Optional: Filtering
    filters = {
        'date': request.GET.get('date', ''),
        'project': request.GET.get('project', '')
    }

    if filters['date']:
        reports = reports.filter(date=filters['date'])
    if filters['project']:
        reports = reports.filter(project_id=filters['project'])

    return render(request, 'dashboard/engineer/weekly_report_list.html', {
        'reports': reports,
        'filters': filters
    })


@login_required(login_url='/users/login')
def weekly_report_detail(request, pk):
    report = get_object_or_404(
        WorkReport,
        pk=pk,
        report_type='weekly'
    )

    return render(request, 'dashboard/engineer/weekly_report_detail.html', {
        'report': report
    })


@login_required(login_url='/users/login')
def create_completion_report(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    # Prevent duplicate completion report
    if WorkReport.objects.filter(
        project=project,
        report_type='completion'
    ).exists():
        messages.warning(request, "Completion report already exists.")
        return redirect('completion_report_detail', project_id=project.id)

    if request.method == "POST":
        report = WorkReport.objects.create(
            user=request.user,
            project=project,
            report_type='completion',
            work_type='other',
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            status='completed',
            progress=100,
            issues=request.POST.get('issues'),
            before_image=request.FILES.get('before_image'),
            after_image=request.FILES.get('after_image'),
        )

        return redirect('completion_report_detail', project_id=project.id)

    return render(request, 'dashboard/engineer/completion_report_form.html', {
        'project': project
    })



@login_required(login_url='/users/login')
def completion_report_detail(request, project_id):
    project = get_object_or_404(Project, id=project_id)

    report = get_object_or_404(
        WorkReport,
        project=project,
        report_type='completion'
    )

    return render(request, 'dashboard/engineer/completion_report_detail.html', {
        'report': report
    })


@login_required(login_url='/users/login')
def completion_report_list(request):

    # 🔹 Base queryset (only completion reports)
    reports = WorkReport.objects.filter(
        report_type='completion'
    ).select_related('project', 'user')

    # 🔹 Role-based filtering
    if request.user.role != "admin":
        try:
            employee = Employee.objects.get(user=request.user)
            reports = reports.filter(project__engineer=employee)
        except Employee.DoesNotExist:
            reports = reports.none()

    # 🔹 Filters
    date = request.GET.get('date')
    status = request.GET.get('status')
    project = request.GET.get('project')

    if date:
        reports = reports.filter(date=date)

    if status:
        reports = reports.filter(status=status)

    if project:
        reports = reports.filter(project_id=project)

    # 🔹 Ordering
    reports = reports.order_by('-date')

    # 🔹 Projects for dropdown filter
    if request.user.role == "admin":
        projects = Project.objects.all()
    else:
        try:
            employee = Employee.objects.get(user=request.user)
            projects = Project.objects.filter(engineer=employee)
        except Employee.DoesNotExist:
            projects = Project.objects.none()

    context = {
        'reports': reports,
        'projects': projects,
        'filters': {
            'date': date,
            'status': status,
            'project': project,
        }
    }

    return render(
        request,
        'dashboard/engineer/completion_report_list.html',
        context
    )




@login_required(login_url='/users/login')
def download_report(request, type, id=None):
    context = {}
    template = ""

    # 🔹 EXPENSE REPORT
    if type == "expense" and id:
        report = ExpenseReport.objects.get(id=id)
        template = "dashboard/expense_pdf.html"
        context = {
            "report": report,
            "items": report.items.all(),
            "total": report.total_amount
        }

    # 🔹 MONTHLY EXPENSE REPORT
    elif type == "monthly_expense":
        month_input = request.GET.get('month')
        today = timezone.now()
        if month_input:
            year, month = map(int, month_input.split('-'))
        else:
            month = today.month
            year = today.year
        reports = ExpenseReport.objects.filter(
            expense_date__month=month,
            expense_date__year=year,
            status='approved'
        ).select_related('project').prefetch_related('items')
        total_expense = sum([r.total_amount for r in reports])
        template = "dashboard/monthly_expense_pdf.html"
        context = {
            "reports": reports,
            "total_expense": total_expense,
            "month": month,
            "year": year,
        }

    # 🔹 FEASIBILITY REPORT
    elif type == "feasibility" and id:
        report = FeasibilityReport.objects.select_related("project", "submitted_by").get(id=id)
        template = "dashboard/feasibility_pdf.html"
        context = {
            "report": report,
            "project": report.project,
            "client": report.project.lead,
        }

    # 🔹 WORK REPORTS (daily, weekly, completion)
    elif type == "work":
        try:
            report = WorkReport.objects.get(id=id, user=request.user)
        except WorkReport.DoesNotExist:
            return HttpResponse("Report not found", status=404)

        # Build absolute image URLs for PDF
        before_image_url = request.build_absolute_uri(report.before_image.url) if report.before_image else None
        after_image_url = request.build_absolute_uri(report.after_image.url) if report.after_image else None

        template = "dashboard/work_pdf.html"
        context = {
            "report": report,
            "before_image_url": before_image_url,
            "after_image_url": after_image_url,
        }


    # 🔹 SERVICE REPORT
    elif type == "service" and id:
        report = ServiceReport.objects.get(id=id)
        template = "dashboard/service_pdf.html"
        report_image_url = request.build_absolute_uri(report.images.url) if report.images else None
        context = {
            "report": report,
            "report_image_url": report_image_url,
            "engineer_name": report.report_by.name if report.report_by else "N/A",
        }

    # 🔹 INVOICE
    elif type == "invoice" and id:
        invoice = Invoice.objects.get(id=id)
        template = "dashboard/invoice_pdf.html"
        context = {
            "invoice": invoice,
            "payments": invoice.payments.all(),
            "total_paid": sum(p.amount for p in invoice.payments.all()),
            "balance": invoice.total_amount - sum(p.amount for p in invoice.payments.all())
        }

    # 🔹 PURCHASE ORDER
    elif type == "purchase" and id:
        po = PurchaseOrder.objects.get(id=id)
        template = "dashboard/purchase_pdf.html"
        context = {
            "po": po,
            "items": po.items.all(),
            "total": po.total_amount
        }

    # 🔹 COSTING REPORT
    elif type == "costing" and id:
        costing = ProjectCosting.objects.get(id=id)
        template = "dashboard/costing_pdf.html"
        context = {
            "costing": costing,
            "project": costing.project,
            "estimated": costing.estimated_cost,
            "actual": costing.actual_cost,
            "revenue": costing.revenue,
            "profit": costing.profit,
        }

    else:
        return HttpResponse("Invalid report", status=400)

    # 🔹 GENERATE PDF
    html = render_to_string(template, context)
    pdf = HTML(string=html).write_pdf()

    # File name logic
    filename = type
    if type == "work":
        filename += f"_{context.get('report_type', 'daily')}_{timezone.now().date()}"
    elif type in ['service', 'expense', 'feasibility', 'invoice', 'purchase', 'costing'] and id:
        filename += f"_{id}_{timezone.now().date()}"

    return HttpResponse(
        pdf,
        content_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}.pdf"'
        }
    )



@login_required(login_url='/users/login')
def view_project_layouts(request):
    projects = Project.objects.filter(installation_tasks__assigned_to=request.user).distinct()
    return render(request,'dashboard/staff/layouts.html',{'projects':projects})


@login_required(login_url='/users/login')
def project_layout_detail(request, pid):

    project = Project.objects.get(id=pid)
    files = project.media.filter(category='design_document')
    context = {
            'project': project,
            'files': files
        }

    return render(request,'dashboard/staff/layout_detail.html',context)



@login_required(login_url='/users/login')
def licensing_list(request):
    user = request.user

    projects = Project.objects.filter(status__in = ['structure','electrical','licensing'])

    # 🔥 ADD EXTRA DATA
    project_data = []

    for project in projects:
        total_tasks = project.licensing_tasks.count()
        completed_tasks = project.licensing_tasks.filter(status='completed').count()
        pending_tasks = total_tasks - completed_tasks

        progress = 0
        if total_tasks > 0:
            progress = int((completed_tasks / total_tasks) * 100)

        project_data.append({
            'project': project,
            'pending_tasks': pending_tasks,
            'progress': progress
        })

    return render(request, 'dashboard/liaison/licensing_list.html', {
        'project_data': project_data
    })

@login_required(login_url='/users/login')
def licensing_dashboard(request, id):
    project = get_object_or_404(Project, id=id)
    tasks = project.licensing_tasks.select_related('assigned_to').prefetch_related('documents')

    # Determine user role
    user_role = request.user.role
    admin_access = user_role == 'admin'
    liaison_access = user_role == 'liaison'

    today = date.today()
    now = timezone.now()
    active_phase_key = None  # Default active phase

    # =========================
    # PHASE-WISE PROGRESS LOGIC (used both POST & GET)
    # =========================
    phase_map = {
        'preparation': 'Preparation',
        'kseb': 'KSEB',
        'mnre': 'MNRE',
        'subsidy': 'Subsidy'
    }

    def get_color(progress):
        if progress < 30:
            return 'bg-danger'
        elif progress < 70:
            return 'bg-warning'
        return 'bg-success'

    # Build phase_data
    phase_data = []
    total_tasks = tasks.count()
    total_completed = tasks.filter(status='completed').count()
    total_progress = int((total_completed / total_tasks) * 100) if total_tasks else 0

    for key, label in phase_map.items():
        qs = tasks.filter(phase=key)
        total = qs.count()
        completed = qs.filter(status='completed').count()
        progress = int((completed / total) * 100) if total else 0
        overdue = qs.filter(due_date__lt=now, status__in=['new', 'in_progress']).count()
        phase_data.append({
            'key': key,
            'label': label,
            'tasks': qs,
            'progress': progress,
            'color': get_color(progress),
            'overdue': overdue,
            'total': total,
            'completed': completed
        })

    # =========================
    # HANDLE POST ACTIONS
    # =========================
    if request.method == "POST":
        action = request.POST.get("action")
        task_id = request.POST.get("task_id")
        task = get_object_or_404(LicensingTask, id=task_id)

        # Mark the updated task's phase as active
        active_phase_key = task.phase

        # -------- STATUS UPDATE --------
        if action == "update_status" and (liaison_access or admin_access):
            status = request.POST.get("status")
            if status in ['new', 'in_progress', 'completed']:
                task.status = status
                if status == 'completed':
                    task.completed_at = now
                task.save()

        # -------- DOCUMENT UPLOAD --------
        elif action == "upload_doc" and (liaison_access or admin_access):
            file = request.FILES.get("file")
            caption = request.POST.get("caption")
            form_id = request.POST.get('form_id')

            if form_id and request.session.get('last_form_id') == form_id:
                pass  # Prevent duplicate upload
            else:
                request.session['last_form_id'] = form_id
                if file:
                    exists = LicensingDocument.objects.filter(task=task, file=file.name).exists()
                    if not exists:
                        LicensingDocument.objects.create(
                            task=task,
                            file=file,
                            caption=caption,
                            uploaded_by=request.user
                        )

        # -------- DUE DATE UPDATE --------
        elif action == "update_due_date" and admin_access:
            new_due_date = request.POST.get("due_date")
            if new_due_date:
                task.due_date = new_due_date
                task.save()

        # -------- NOTIFY LIAISON OFFICER --------
        elif action == "notify_officer" and admin_access:
            officer = task.assigned_to
            if officer:
                create_notification(
                    recipient=officer,
                    sender=request.user,
                    title=f"Message from Admin",
                    message=f"Please speed up the task '{task.name}' in project '{project.title}'.",
                    link=reverse("licensing_dashboard", kwargs={'id': project.id}),
                    category="admin"
                )

    # =========================
    # GET REQUEST: default active tab
    # =========================
    if not active_phase_key and phase_data:
        active_phase_key = phase_data[0]['key']

    return render(request, 'dashboard/liaison/licensing_dashboard.html', {
        'project': project,
        'phase_data': phase_data,
        'total_progress': total_progress,
        'total_color': get_color(total_progress),
        'now': now,
        'today': today,
        'admin_access': admin_access,
        'liaison_access': liaison_access,
        'active_phase_key': active_phase_key,
    })



@login_required(login_url='/users/login')
def licensing_by_phase(request, phase):
    user = request.user

    tasks = LicensingTask.objects.filter(
        assigned_to=user,
        phase=phase
    ).exclude(status='completed')

    project_ids = tasks.values_list('project_id', flat=True).distinct()

    projects = Project.objects.filter(id__in=project_ids)

    return render(request, 'dashboard/liaison/licensing_list.html', {
        'projects': projects,
        'current_phase': phase
    })

@require_POST
@login_required(login_url='/users/login')
def complete_licensing_task(request, id):
    task = get_object_or_404(LicensingTask, id=id)

    task.mark_completed()

    return JsonResponse({
        'success': True,
        'task_id': task.id
    })



@login_required(login_url='/users/login')
def energisation_projects(request):
    projects = Project.objects.filter(status='energisation').order_by('-id')

    return render(request, 'dashboard/admin/energisation_projects.html', {
        'projects': projects
    })


@login_required(login_url='/users/login')
def mark_project_completed(request, id):
    project = get_object_or_404(Project, id=id)

    if request.method == 'POST':
        project.status = 'completed'
        project.save()

    return redirect('energisation_projects')