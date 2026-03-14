from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q

from .utils import generate_temp_password, create_notification
from .models import *
from .forms import *


from public.models import *
from public.forms import BlogPostForm


from crm.models import *


from users.utils import create_notification


from ollama import chat



# ======================================================
#           AUTHENTICATION & AUTHORIZATION
# ======================================================
# Handles user login, logout, role-based dashboard routing,
# and password change functionality.

def login_page(request):
    if request.method =="POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request,username=username,password=password)

        if user:
            login(request,user)
            create_notification(
                            recipient=user,
                            title='New Login',
                            message='You logged in to Lumora Solar CRM successfully.',
                            )
            return redirect(dashboard)
        else:
            messages.error(request,'Invalid Username or Password!!!')
    
    return render(request,'public_view/login.html')


def logout_page(request):
    logout(request)
    return redirect(login_page)


@login_required(login_url='/users/login')
def dashboard(request):
    if request.user.role == 'admin':
        return redirect(admin_dashboard)
    elif request.user.role == 'engineer':
        return redirect(engineer_dashboard)
    elif request.user.role == 'accountant':
        return redirect(accountant_dashboard)
    elif request.user.role == 'sales':
        return redirect(sales_dashboard)
    elif request.user.role == 'sales':
        return redirect(staff_dashboard)


@login_required(login_url='/users/login')    
def admin_dashboard(request):
    if request.user.role is None:
        return redirect(dashboard)
    total_leads = Lead.objects.count()
    converted = Lead.objects.filter(status='converted').count()
    active_projects = Project.objects.exclude(status='completed').count()
    context = {
        "total_leads": total_leads,
        "converted":converted,
        "not_converted":total_leads - converted,
        "recent_leads": Lead.objects.order_by('-created_at')[:5],
        "active_projects": active_projects
    }

    return render(request,'dashboard/admin/admin.html',context)


@login_required(login_url='/users/login')
def engineer_dashboard(request):
    if request.user.role != 'engineer':
        return redirect(dashboard)

    if request.user.must_change_password:
        create_notification(
                            recipient=request.user,
                            title='Change Password',
                            message='Please update your temperory password',
                            link='password'
                            )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)
    p_assigned = Project.objects.filter(engineer=profile).count()
    p_active = Project.objects.filter(engineer=profile).exclude(status='completed').count()
    p_completed = Project.objects.filter(engineer=profile,status='completed').count()

    context = {
        'profile': profile,
        'assigned':p_assigned,
        'active':p_active,
        'completed':p_completed,
    }
    return render(request,'dashboard/engineer/engineer.html', context)

@login_required(login_url='/users/login')
def accountant_dashboard(request):

    request.user.role == 'accountant'
    if request.user.role != 'accountant':
        return redirect(dashboard)

    if request.user.must_change_password:
        create_notification(
                            recipient=request.user,
                            title='Change Password',
                            message='Please update your temperory password',
                            link='password'
                            )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)
    return render(request,'dashboard/accountant/accountant.html',{'profile':profile})


@login_required(login_url='/users/login')
def sales_dashboard(request):

    request.user.role == 'sales'
    if request.user.role != 'sales':
        return redirect(dashboard)

    if request.user.must_change_password:
        create_notification(
                            recipient=request.user,
                            title='Change Password',
                            message='Please update your temperory password',
                            link='password'
                            )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)
    total_leads = Lead.objects.count()

    context = {
        "total_leads": total_leads,
        "recent_leads": Lead.objects.order_by('-created_at')[:5],
        'profile':profile
    }
    return render(request,'dashboard/sales/sales.html',)

@login_required(login_url='/users/login')
def staff_dashboard(request):

    if request.user.role != 'staff':
        return redirect(dashboard)

    if request.user.must_change_password:
        create_notification(
                            recipient=request.user,
                            title='Change Password',
                            message='Please update your temperory password',
                            link='password'
                            )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)
    return render(request,'dashboard/staff/staff.html',{'profile':profile})
    

class ChangePassword(PasswordChangeView):
    template_name = 'dashboard/change_password.html'
    success_url = reverse_lazy('dashboard')

    def form_valid(self, form):

        self.request.user.must_change_password = False
        self.request.user.save()

        return super().form_valid(form)




# ======================================================
#               EMPLOYEE MANAGEMENT
# ======================================================
# Handles employee creation, role-based profile creation,
# employee listing, viewing, editing, and profile management.


@login_required(login_url='/users/login')
def add_employee(request):

    role = request.POST.get('role') or request.GET.get('role')

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, role=role)

        username = request.POST.get('username')
        email = request.POST.get('email')

        if form.is_valid():
            try:
                with transaction.atomic():

                    temp_password = generate_temp_password()

                    user = CustomUser.objects.create(
                        username=username,
                        email=email,
                        role=role
                    )

                    user.set_password(temp_password)
                    user.must_change_password = True
                    user.save()

                    employee = form.save(commit=False)
                    employee.user = user
                    employee.save()

                    send_mail(
                        subject="Welcome to Zyphora Solar",
                        message=f"""
                                Hi {employee.name},

                                Welcome to Zyphora Solar!

                                Your account has been created.

                                Username: {username}
                                Temporary Password: {temp_password}

                                Please login and change your password immediately.

                                Login here:
                                http://127.0.0.1:8000/users/login

                                Regards,
                                Zyphora Solar Team
                                """,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    create_notification(
                        recipient=request.user,
                        title="New Employee Added",
                        message=f"{employee.name} ({employee.designation}) has joined the team.",
                        sender=request.user,
                        link=reverse('emplist'),
                        category="employee"
                    )

                    create_notification(
                        recipient=user,
                        title="Welcome to the Team!",
                        message=f"Hi {employee.name}, welcome to Zyphora Solar! We're excited to have you onboard as {employee.designation}.",
                        sender=None,
                        link=reverse('dashboard')
                    )
                    messages.success(request, "Employee created successfully")
                    return redirect(all_employees)

            except Exception as e:
                messages.error(request, str(e))
                print(str(e))

    else:
        form = EmployeeForm(role=role)

    return render(request, 'dashboard/admin/emp_reg.html', {'form': form})

@login_required(login_url='/users/login')
def all_employees(request):
    role = request.GET.get('role','')
    query = request.GET.get("q")
    employees = Employee.objects.all()

    if query:
        employees = employees.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(user__username__icontains=query)
        )

    if role:
        employees = employees.filter(user__role=role)

    role_choices = [i for i in CustomUser.ROLE_CHOICES if i[0] != 'admin']

    context = {
        'employees': employees,
        'role_choices': role_choices,
        'role': role
    }
    return render(request,'dashboard/admin/emp_list.html', context)


@login_required(login_url='/users/login')
def view_employee(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    return render(request,'dashboard/admin/view_emp.html',{'employee': emp})

@login_required(login_url='/users/login')
def edit_employee(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            employee = form.save(commit=False)
            if 'profile_pic' in request.FILES:
                employee.profile_pic = request.FILES['profile_pic']

            employee.save()
            return redirect('viewemp', emp.id)
    else:
        form = EmployeeForm(instance=emp)

    context = {
        'form': form,
        'employee': emp
    }
    return render(request,'dashboard/admin/edit_emp.html', context)



@login_required(login_url='/users/login')
def view_profile(request):
    emp = Employee.objects.get(user=request.user)

    return render(request,'dashboard/profile.html',{'employee':emp})



# ======================================================
#               BLOG MANAGEMENT
# ======================================================
# Handles blog creation, editing, viewing, listing,
# deletion, and AI formatting for SEO-friendly content.

@login_required(login_url='/users/login')
def blog_list(request):
    blog =BlogPost.objects.order_by('-published_date')
    return render(request,'dashboard/admin/blog_list.html',{'blog':blog})



@login_required(login_url='/users/login')
def view_post(request,id):
    post = BlogPost.objects.get(id=id)
    return render(request,'dashboard/admin/view_blog.html',{'post':post})



@login_required(login_url='/users/login')
def edit_post(request, bid):
    post = BlogPost.objects.get(id=bid)

    if request.method == 'POST':

        plain_content = request.POST.get('content')

        response = chat(
            model='llama3.2',
            messages=[
                {
                    'role': 'user',
                    'content': f"""
                                You are a professional SEO blog writer.

                                Convert the following blog content into clean HTML format.

                                Title: {post.title}
                                Content: {plain_content}

                                Formatting rules:
                                - Use <p> for paragraphs
                                - Use <h3> for sections
                                - Use <h4> for subsections
                                - Use <ul> and <li> for lists
                                - Use <strong> for important text

                                Return ONLY HTML.
                                """
                }
            ],
            options={'temperature': 0.6}
        )

        html_content = response.message.content

        form = BlogPostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            post = form.save(commit=False)
            post.content = html_content
            post.save()

            messages.success(request, 'Post updated successfully')
            return redirect(view_post, id=post.id)

    else:
        post.content = strip_tags(post.content)
        form = BlogPostForm(instance=post)

    return render(request, 'dashboard/admin/edit_blog.html', {'form': form, 'post': post})


@login_required(login_url='/users/login')
def delete_post(request,bid):
    post = BlogPost.objects.get(id=bid)
    post.delete()
    messages.warning(request,'Post deleted')
    return redirect(blog_list)



@login_required(login_url='/users/login')
def add_post(request):

    if request.method == 'POST':
        form = BlogPostForm(request.POST, request.FILES)

        if form.is_valid():
            post = form.save(commit=False)

            plain_content = post.content

            response = chat(
                model='llama3.2',
                messages=[
                    {
                        'role': 'user',
                        'content': f"""
                                    You are a professional SEO blog writer.

                                    Convert the following blog content into clean structured HTML suitable for a blog article.

                                    Title: {post.title}
                                    Content: {plain_content}

                                    Formatting rules:

                                    - Use <p> for paragraphs
                                    - Use <h3> for section headings
                                    - Use <h4> for subheadings
                                    - Use <ul> and <li> for lists
                                    - Use <strong> for important phrases
                                    - Use <table> for comparisons if needed

                                    Return ONLY valid HTML.
                                    Do not include explanations.
                                    """
                    }
                ],
                options={
                    'temperature': 0.6
                }
            )

            post.content = response.message.content

            if not post.summary:

                response = chat(
                    model='llama3.2',
                    messages=[
                        {
                            'role': 'user',
                            'content': f"""
                                        You are a professional content writer. Write a blog excerpt.

                                        Blog Post Title: {post.title}
                                        Blog Post Content: {plain_content}

                                        Keep it under 30 words.
                                        """
                        }
                    ],
                    options={'temperature': 0.7}
                )

                post.summary = response.message.content

            post.save()

            messages.success(request, "Blog post added successfully!")

            return redirect('blogposts')

    else:
        form = BlogPostForm()

    return render(request, 'dashboard/admin/add_blog.html', {'form': form})



# ======================================================
#               NOTIFICATIONS
# ======================================================
# Handles fetching, viewing, marking as read, deleting,
# and sending notifications to admins and assigned users.




@login_required(login_url='/users/login')
def mark_as_read(request, nid):
    notification = get_object_or_404(Notification, id=nid, recipient=request.user)
    notification.is_read = True
    notification.save()
    return redirect(request.META.get('HTTP_REFERER', 'notifications'))

@login_required(login_url='/users/login')
def mark_all_as_read(request):
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)

    return redirect(request.META.get('HTTP_REFERER', '/'))



@login_required(login_url='/users/login')
def get_notifications(request):

    if not request.user.is_authenticated:
        return JsonResponse({"notifications": [], "unread_count": 0})

    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]

    data = []

    for n in notifications:
        data.append({
            "id": n.id,
            "title": n.title or "No Title",       
            "link": n.link or "#", 
            "is_read": n.is_read,
            "time": n.created_at.strftime("%b %d, %H:%M"),
        })

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return JsonResponse({
        "notifications": data,
        "unread_count": unread_count
    })

@login_required(login_url='/users/login')
def notifications(request, ntype="all"):
    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')

    if ntype == "unread":
        notifications = notifications.filter(is_read=False)
    elif ntype in ["crm", "project", "finance", "employee", "system"]:
        notifications = notifications.filter(category=ntype)

    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications_page = paginator.get_page(page_number)

    # Prepare headings and icons for template
    headings = {
        "all": "All Notifications",
        "unread": "Unread Notifications",
        "crm": "Client Updates",
        "lead": "Lead Updates",
        "project": "Project Alerts",
        "finance": "Finance Alerts",
        "employee": "Employee Alerts",
        "system": "System Alerts",
        "admin": "Admin Alerts"
    }

    icons = {
        "crm": "bi-person-plus-fill text-primary",
        "lead": "bi-person-plus-fill text-primary",
        "project": "bi-briefcase-fill text-success",
        "finance": "bi-cash-coin text-warning",
        "employee": "bi-people-fill text-info",
        "system": "bi-gear-fill text-secondary",
        "tasks":"bi-list-check",
        "material":"bi-box-seam",
        "service":"bi-wrench-adjustable",
        "admin":"bi-bell-fill text-danger"
    }

    badges = {
        "crm": "bg-primary",
        "lead": "bg-primary",
        "project": "bg-success",
        "finance": "bg-warning text-dark",
        "employee": "bg-info text-dark",
        "system": "bg-secondary",
        "admin":"bg-danger"
    }

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    context = {
        "notifications": notifications_page,
        "ntype": ntype,
        "headings": headings,
        "icons": icons,
        "badges": badges,
        "unread_count": unread_count
    }

    return render(request, "dashboard/notifications.html", context)


@login_required(login_url='/users/login')
def delete_notification(request, nid):

    notification = get_object_or_404(
        Notification,
        id=nid,
        recipient=request.user
    )

    notification.delete()

    return redirect(request.META.get('HTTP_REFERER', 'all_notifications'))

@login_required(login_url='/users/login')
def delete_all_notifications(request):
    Notification.objects.filter(recipient=request.user).delete()
    messages.success(request, "All notifications deleted.")
    return redirect(request.META.get('HTTP_REFERER', 'all_notifications'))


def notify_admins_and_assigned(sender, instance, title, message, link, admin_cat, emp_cat):

    admins = CustomUser.objects.filter(role='admin')

    # Notify admins
    for admin in admins:
        create_notification(
            recipient=admin,
            sender=sender,
            title=title,
            message=message,
            link=link,
            category=admin_cat
        )

    assigned_staff = None
    if hasattr(instance, 'assigned_to'):
        assigned_staff = instance.assigned_to
    elif hasattr(instance, 'engineer') and instance.engineer:
        assigned_staff = instance.engineer.user 

    # Notify staff if they exist and are not admins
    if assigned_staff and not admins.filter(id=assigned_staff.id).exists():
        create_notification(
            recipient=assigned_staff,
            sender=sender,
            title=title,
            message=message,
            link=link,
            category=emp_cat
        )


def notifyEmployee(request,id):
    sender = request.user
    emp = Employee.objects.get(id=id)
    recipient = emp.user

    if request.method == "POST":
        title = request.POST.get('title')
        message = request.POST.get('message')
        create_notification(
            sender=sender,
            recipient=recipient,
            title=title or "Message from Admin",
            message=message,
            category="admin"
        )
        messages.success(request,"Message send successfully")

        return redirect(notifyEmployee,id=id)
    return render(request,'dashboard/notify.html',{'emp': emp})
