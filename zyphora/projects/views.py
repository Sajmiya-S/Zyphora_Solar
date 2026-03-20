from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from datetime import date

from .models import *
from .forms import *


from users.views import notify_admins_and_assigned


from finance.models import ProjectCosting


from crm.models import Lead








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


@login_required
def update_project(request, pid):
    project = get_object_or_404(Project, id=pid)
    link = reverse('project_detail', kwargs={'pid': project.id})

    status_order = [status[0] for status in Project.STATUS_CHOICES]

    # Fields to track updates (excluding status, which is handled in model)
    track_fields = ["engineer", "description", "revenue", "location"]

    def log_field_change(field_name, old_value, new_value):
        if old_value != new_value:
            # Construct readable messages
            if old_value is None and new_value:
                title = f"{field_name} Added"
                message = f"{field_name} set to {new_value}"
            elif old_value and new_value is None:
                title = f"{field_name} Removed"
                message = f"{field_name} was removed"
            else:
                title = f"{field_name} Updated"
                message = f"{field_name} changed from {old_value} to {new_value}"

            # Save activity
            ProjectActivity.objects.create(
                project=project,
                title=title,
                description=message,
                created_by=request.user,
            )

            # Send notifications
            notify_admins_and_assigned(
                sender=request.user,
                instance=project,
                title=title,
                message=message,
                link=link,
                admin_cat="project",
                emp_cat="project"
            )

    if request.method == "POST":
        old_data = {field: getattr(project, field) for field in track_fields}
        old_start = project.start_date
        old_end = project.end_date

        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            with transaction.atomic():
                form.save()

                # Log all tracked fields
                for field in track_fields:
                    log_field_change(field.replace("_", " ").title(), old_data[field], getattr(project, field))

                # Log start/end date changes separately
                log_field_change("Start Date", old_start, project.start_date)
                log_field_change("End Date", old_end, project.end_date)

                # Handle multiple image uploads
                images = request.FILES.getlist('images')
                captions = request.POST.getlist('captions') or []
                uploaded_count = 0
                for i, img in enumerate(images):
                    caption = captions[i] if i < len(captions) else ""
                    image_obj = ProjectImage.objects.create(image=img, caption=caption)
                    project.gallery.add(image_obj)
                    uploaded_count += 1

                if uploaded_count:
                    title = "Project Images Added"
                    message = f"{uploaded_count} images uploaded to {project.title}"

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
        "images": project.gallery.all(),
        "status_order": status_order,
        "progress_percent": project.progress_percent,
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
def add_project_images(request,pid):
    project = Project.objects.get(id=pid)
    if request.method == "POST":

        images = request.FILES.getlist('images')
        captions = request.POST.get('captions')
        uploaded_count = 0
        for i, img in enumerate(images):
            caption = captions[i] if i < len(captions) else ""
            image_obj = ProjectImage.objects.create(image=img, caption=caption)
            project.gallery.add(image_obj)
            uploaded_count += 1

        if uploaded_count:
            title = "Project Images Added"
            message = f"{uploaded_count} images uploaded to {project.title}"

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
                link=reverse('project_gallery',kwargs={'pid':project.id}),
                admin_cat="project",
                emp_cat="project"
            )
        return redirect(request.META.get("HTTP_REFERER"))
    
    return redirect(project_gallery,pid)
    



@login_required(login_url='/users/login')
def delete_project_image(request,id):

    image = ProjectImage.objects.get(id=id)
    pid = image.project.id
    image.delete()

    return redirect(update_project,pid=pid)

@login_required(login_url='/users/login')
def update_image_caption(request,id):
    image = ProjectImage.objects.get(id=id)
    pid = image.project.id
    if request.method == "POST":
        
        form = ProjectImageForm(request.POST,request.FILES,instance=image)
        if form.is_valid():
            form.save()
            return redirect(project_gallery,pid)
      
    return redirect(project_gallery,pid)


@login_required(login_url='/users/login')
def project_gallery(request, pid):

    project = Project.objects.get(id=pid)
    images = project.gallery.all()
    context = {
            'project': project,
            'images': images
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
    task.status = 'completed'
    task.save()
    return redirect(my_tasks)


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
def installation_progress(request):

    engineer = Employee.objects.get(user=request.user)
    projects = Project.objects.filter(engineer=engineer)
    if request.method == "POST":
        # Update status for the project submitted
        project_id = request.POST.get("project_id")
        new_status = request.POST.get("status")
        project = Project.objects.get(id=project_id,engineer=engineer)

        if new_status in [s[0] for s in project.STATUS_CHOICES]:
            project.status = new_status
            project.save()

        return redirect(installation_progress)
    return render(request, "dashboard/installation_progress.html",{'projects':projects})


@login_required(login_url='/users/login')
def design_list(request):
    # Admin sees all projects, engineer only sees assigned ones
    if request.user.role == "admin":
        projects = Project.objects.all()
    else:
        engineer = Employee.objects.get(user=request.user)
        projects = Project.objects.filter(engineer=engineer)
    # Determine phase dynamically for each project
    projects_with_phase = []
    for project in projects:
        docs = project.design_documents.all()
        if not docs.exists():
            current_phase = "preparation"
        elif docs.filter(approved=False).exists():
            current_phase = "preparation"
        elif not hasattr(project, 'costing'):
            current_phase = "approval"
        else:
            current_phase = "costing"

        projects_with_phase.append({
            "project": project,
            "current_phase": current_phase
        })

    context = {
        "projects_with_phase": projects_with_phase
    }
    return render(request, "dashboard/design_list.html", context)



@login_required(login_url='/users/login')
def design_detail(request, pid):
    project = get_object_or_404(Project, id=pid)

    docs = project.design_documents.all()
    if not docs.exists():
        current_phase = "preparation"
    elif docs.filter(approved=False).exists():
        current_phase = "preparation"
    elif not hasattr(project, 'costing'):
        current_phase = "approval"
    else:
        current_phase = "costing"

    if request.method == "POST":
        # Engineer uploads designs
        if request.user.role == "engineer" and current_phase == "preparation":
            files = request.FILES.getlist("design_files")
            captions = request.POST.getlist("captions") or []
            for i, f in enumerate(files):
                caption = captions[i] if i < len(captions) else ""
                ProjectDesignDocument.objects.create(
                    project=project,
                    file=f,
                    caption=caption,
                    uploaded_by=request.user
                )

        # Admin approves designs
        if request.user.role == "admin" and current_phase == "preparation":
            approve_ids = request.POST.getlist("approve_docs")
            ProjectDesignDocument.objects.filter(id__in=approve_ids).update(approved=True)

        # Admin enters costing
        if request.user.role == "admin" and current_phase == "approval":
            cost = request.POST.get("cost")
            if cost:
                ProjectCosting.objects.create(project=project, cost=cost, entered_by=request.user)

        return redirect(design_detail, pid=pid)

    context = {
        "project": project,
        "design_documents": docs,
        "current_phase": current_phase
    }
    return render(request, "dashboard/design_detail.html", context)





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

    return render(request, 'dashboard/add_service_report.html', {
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
    report = ServiceReport.objects.get(id=rid,service_request__project__lead__assigned_to=request.user)

    return render(request, 'dashboard/sales/service_report_detail.html', {'report': report})




@login_required(login_url='/users/login')
def installation_tasks(request):
    tasks = InstallationTask.objects.filter(assigned_to=request.user)
    return render(request, "dashboard/staff/installation_tasks.html", {"tasks": tasks})


@login_required(login_url='/users/login')
def staff_projects(request):
    projects = Project.objects.filter(installation_tasks__assigned_to=request.user).distinct()
    return render(request, "dashboard/staff/projects.html", {"projects": projects})





