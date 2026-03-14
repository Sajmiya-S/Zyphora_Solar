from django.shortcuts import render,get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q


from .models import *
from .forms import *


from users.views import notify_admins_and_assigned














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

    if request.user.role == "engineer":
        employee = Employee.objects.filter(user=request.user).first()
        if employee:
            projects = projects.filter(engineer=employee)

    if status:
        projects = projects.filter(status=status)

    if query:
        projects = projects.filter(
            Q(title__icontains=query) |
            Q(project_type__icontains=query) |
            Q(engineer__user__username__icontains=query)
        )


    projects = projects.order_by('-created_at')

    context = {
        'projects': projects,
        'status_choices': Project.STATUS_CHOICES,
        'status': status
    }
    return render(request, 'dashboard/all_projects.html', context)


@login_required
def update_project(request, pid):
    project = get_object_or_404(Project, id=pid)
    link = reverse('project_detail', kwargs={'pid': project.id})
    
    # Calculate progress
    status_order = [status[0] for status in Project.STATUS_CHOICES]
    progress_map = {status: 5 + i*9 for i, status in enumerate(status_order)}
    progress_percent = progress_map.get(project.status, 0)

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
        "progress_percent": progress_percent,
    }

    return render(request, "dashboard/edit_project.html", context)


@login_required(login_url='/users/login')
def view_project(request,pid):
    project = Project.objects.get(id=pid)
    activities = project.activities.order_by('-created_at') 

    status_order = [status[0] for status in project.STATUS_CHOICES]
    current_index = status_order.index(project.status)
    completed_stages = status_order[:current_index]

    progress_map = {}
    progress = 5
    for status in status_order:
        progress_map[status] = progress
        progress += 10
    progress = progress_map.get(project.status,0)

    context = {
        'project':project,
        'activities':activities,
        'progress':progress,
        'completed_stages':completed_stages
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




