from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from django.utils.html import strip_tags
from django.utils.timezone import now
from django.http import JsonResponse
from django.urls import reverse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q,Sum,Count, Avg
from django.views.decorators.http import require_POST
from datetime import date



from .utils import generate_temp_password, create_notification
from .models import *
from .forms import *


from public.models import *
from public.forms import BlogPostForm

from projects.models import *

from crm.models import *


from users.utils import create_notification


from finance.models import *


from ollama import chat
import calendar
import json

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
    elif request.user.role == 'staff':
        return redirect(staff_dashboard)
    elif request.user.role == 'liaison':
        return redirect(liaison_dashboard)


@login_required(login_url='/users/login')    
def admin_dashboard(request):
    if request.user.role is None:
        return redirect('dashboard')

    # ---- Leads ----
    total_leads = Lead.objects.count()
    converted = Lead.objects.filter(status='converted').count()
    not_converted = total_leads - converted
    recent_leads = Lead.objects.order_by('-created_at')[:5]

    # ---- Projects ----
    active_projects = Project.objects.exclude(status='completed').count()

    # ---- Revenue & Pending Payments ----
    revenue = sum([pc.revenue for pc in ProjectCosting.objects.all()])

    pending_payments = Invoice.objects.annotate(
        paid_amount=Sum('payments__amount')
    ).aggregate(
        total_pending=Sum('total_amount') - Sum('paid_amount')
    )['total_pending'] or 0

    # ---- Project Type Distribution ----
    project_types = ['on-grid','off-grid','hybrid','leakproof','commercial']
    project_counts = [Project.objects.filter(project_type=ptype).count() for ptype in project_types]

    # ---- Project Status Distribution ----
    statuses = ['site_visit', 'design', 'installation', 'electrical', 'energisation']
    status_counts = [Project.objects.filter(status=status).count() for status in statuses]

    # ---- Context ----
    context = {
        "total_leads": total_leads,
        "converted": converted,
        "not_converted": not_converted,
        "recent_leads": recent_leads,
        "active_projects": active_projects,
        "revenue": revenue,
        "pending_payments": pending_payments,
        "project_types": project_types,
        "project_counts": project_counts,
        "statuses": statuses,
        "status_counts": status_counts
    }

    return render(request, 'dashboard/admin/admin.html', context)


@login_required(login_url='/users/login')
def engineer_dashboard(request):

    if request.user.role != 'engineer':
        return redirect('dashboard')

    if request.user.must_change_password:
        create_notification(
            recipient=request.user,
            title='Change Password',
            message='Please update your temporary password',
            link='password'
        )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)

    # ================= KPI =================
    p_assigned = Project.objects.filter(engineer=profile).count()
    p_active = Project.objects.filter(engineer=profile).exclude(status='completed').count()
    p_completed = Project.objects.filter(engineer=profile, status='completed').count()

    tasks = Task.objects.filter(
        assigned_to=request.user,
        status__in=['new', 'in_progress']
    ).count()

    # ================= CHART DATA =================
    project_status = list(
        Project.objects.filter(engineer=profile)
        .values('status')
        .annotate(count=Count('id'))
    )

    project_type = list(
        Project.objects.filter(engineer=profile)
        .values('project_type')
        .annotate(count=Count('id'))
    )

    task_status = list(
        Task.objects.filter(assigned_to=request.user)
        .values('status')
        .annotate(count=Count('id'))
    )

    service_status = list(
        ServiceRequest.objects.filter(assigned_to=profile)
        .values('status')
        .annotate(count=Count('id'))
    )

    # ================= TODAY FILTER =================
    today = timezone.localdate()

    # 🔹 Today's Tasks
    todays_tasks = Task.objects.filter(
        assigned_to=request.user,
        due_date=today
    ).order_by('-created_at')[:5]

    # 🔹 Upcoming Site Visits
    site_visits = SiteVisit.objects.filter(
        engineer=request.user,
        scheduled_date__gte=today
    ).order_by('scheduled_date')[:5]


    context = {
        'profile': profile,

        # KPI
        'assigned': p_assigned,
        'active': p_active,
        'completed': p_completed,
        'tasks': tasks,

        # ✅ SAFE JSON
        'project_status': json.dumps(project_status),
        'project_type': json.dumps(project_type),
        'task_status': json.dumps(task_status),
        'service_status': json.dumps(service_status),

        'todays_tasks': todays_tasks,
        'site_visits': site_visits,
    }

    return render(request, 'dashboard/engineer/engineer.html', context)


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

    # KPIs
    total_revenue = Invoice.objects.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    total_expenses = ExpenseItem.objects.aggregate(total=Sum('amount'))['total'] or 0
    net_profit = total_revenue - total_expenses
    pending_payments = Invoice.objects.filter(status='sent').aggregate(total=Sum('total_amount'))['total'] or 0

    # Revenue vs Expenses Chart (last 6 months)
    months = [(now().month-i) % 12 or 12 for i in reversed(range(6))]
    month_labels = [calendar.month_abbr[m] for m in months]
    revenue_data = []
    expense_data = []

    for m in months:
        rev = Invoice.objects.filter(status='paid', issue_date__month=m).aggregate(total=Sum('total_amount'))['total'] or 0
        exp = ExpenseItem.objects.filter(report__expense_date__month=m).aggregate(total=Sum('amount'))['total'] or 0
        revenue_data.append(float(rev))
        expense_data.append(float(exp))

    finance_chart_data = {
        "labels": month_labels,
        "datasets": [
            {"label":"Revenue", "data":revenue_data, "backgroundColor":"#198754"},
            {"label":"Expenses", "data":expense_data, "backgroundColor":"#dc3545"}
        ]
    }

    # Expense Breakdown Chart
    breakdown = ExpenseItem.objects.values('report__category').annotate(total=Sum('amount'))
    expense_labels = [x['report__category'].title() for x in breakdown]
    expense_values = [float(x['total']) for x in breakdown]
    expense_colors = ['#0d6efd','#ffc107','#6f42c1','#dc3545','#198754']

    expense_breakdown_data = {
        "labels": expense_labels,
        "datasets": [{"data": expense_values, "backgroundColor": expense_colors[:len(expense_values)]}]
    }

    # Recent records
    recent_invoices = Invoice.objects.order_by('-created_at')[:5]
    recent_expense_reports = ExpenseReport.objects.order_by('-created_at')[:5]

    context = {
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
        'pending_payments': pending_payments,
        'finance_chart_data': finance_chart_data,
        'expense_breakdown_data': expense_breakdown_data,
        'recent_invoices': recent_invoices,
        'recent_expense_reports': recent_expense_reports,
        'profile':profile,
    }

    return render(request, 'dashboard/accountant/accountant.html', context)

@login_required(login_url='/users/login')
def sales_dashboard(request):

    if request.user.role != 'sales':
        return redirect('dashboard')

    # Force password change
    if request.user.must_change_password:
        create_notification(
            recipient=request.user,
            title='Change Password',
            message='Please update your temporary password',
            link='password'
        )
        return redirect('password')

    profile = get_object_or_404(Employee, user=request.user)

    leads = Lead.objects.filter(assigned_to=request.user)

    # ================= KPIs =================

    total_leads = leads.count()
    open_leads = leads.exclude(status__in=['converted', 'rejected']).count()
    closed_deals = leads.filter(status='converted').count()

    # ================= FUNNEL =================

    new_count = leads.filter(status='new').count()
    contacted_count = leads.filter(status='contacted').count()
    visit_count = leads.filter(status='site_visit_scheduled').count()
    converted_count = leads.filter(status='converted').count()

    funnel_data = [
        {"status": "New", "count": new_count},
        {"status": "Contacted", "count": contacted_count},
        {"status": "Site Visit", "count": visit_count},
        {"status": "Converted", "count": converted_count},
    ]

    # ================= CONVERSION =================

    conversion_rate = (converted_count / total_leads * 100) if total_leads else 0

    # ================= DROP OFF =================

    drop_contact = new_count - contacted_count
    drop_visit = contacted_count - visit_count
    drop_conversion = visit_count - converted_count

    # ================= CONTEXT =================

    context = {
        "total_leads": total_leads,
        "open_leads": open_leads,
        "closed_deals": closed_deals,

        "recent_leads": leads.order_by('-created_at')[:5],
        "top_leads": leads.order_by('-score')[:5],
        "profile": profile,

        "funnel_data": funnel_data,
        "conversion_rate": round(conversion_rate, 1),

        "drop_contact": drop_contact,
        "drop_visit": drop_visit,
        "drop_conversion": drop_conversion,
    }

    return render(request, 'dashboard/sales/sales.html', context)


@login_required(login_url='/users/login')
def staff_dashboard(request):
    # Only staff can access
    if request.user.role != 'staff':
        return redirect('dashboard')  # redirect non-staff

    # Must change password
    if request.user.must_change_password:
        Notification.objects.create(
            recipient=request.user,
            title='Change Password',
            message='Please update your temporary password',
            link='/users/password/'
        )
        return redirect('password')

    # Staff profile
    profile = get_object_or_404(Employee, user=request.user)

    # Tasks assigned to this staff user
    tasks = Task.objects.filter(assigned_to=request.user).order_by('due_date')

    # Task KPIs
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(status='completed').count()
    pending_tasks = tasks.filter(status__in=['new','in_progress']).count()
    overdue_tasks = tasks.filter(status='overdue').count()

    task_counts = {
        'new': tasks.filter(status='new').count(),
        'in_progress': tasks.filter(status='in_progress').count(),
        'completed': completed_tasks,
        'overdue': overdue_tasks
    }

    # Assigned Projects for staff (technicians)
    projects = Project.objects.filter(installation_tasks__assigned_to=request.user).distinct()  # assigned projects
    assigned_projects = projects.count()


    today = timezone.localdate()
    context = {
        "task_count": Task.objects.filter(assigned_to=request.user).count(),
        "todays_tasks": Task.objects.filter(assigned_to=request.user, due_date=date.today()).count(),
        "pending_tasks": Task.objects.filter(assigned_to=request.user, status='pending').count(),
        "overdue_tasks": Task.objects.filter(assigned_to=request.user, status='pending', due_date__lt=date.today()).count(),
        "installation_count": InstallationTask.objects.filter(assigned_to=request.user).count(),
        "project_count": Project.objects.filter(installation_tasks__assigned_to=request.user).distinct().count(),
        'profile': profile,
        'tasks': tasks,
        'projects': projects,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'assigned_projects': assigned_projects,
        'task_counts': task_counts,
        'today': today,
    }

    return render(request, 'dashboard/staff/staff.html', context)


@login_required(login_url='/users/login')
def liaison_dashboard(request):
    user = request.user

    tasks = LicensingTask.objects.filter(assigned_to=user)

    from django.utils.timezone import now
from django.db.models import Count

@login_required(login_url='/users/login')
def liaison_dashboard(request):
    user = request.user

    tasks = LicensingTask.objects.filter(assigned_to=user)

    # Step Distribution
    step_data = tasks.values('step').annotate(count=Count('id'))

    step_labels = [item['step'] for item in step_data]
    step_counts = [item['count'] for item in step_data]

    # Status Distribution
    status_data = tasks.values('status').annotate(count=Count('id'))

    status_labels = [item['status'] for item in status_data]
    status_counts = [item['count'] for item in status_data]

    context = {
        "assigned_projects": Project.objects.filter(licensing_tasks__assigned_to=user).distinct().count(),
        "licensing_in_progress": tasks.filter(status='in_progress').count(),
        "licensing_completed": tasks.filter(status='completed').count(),
        "pending_tasks": tasks.filter(status='new').count(),

        "todays_tasks": tasks.filter(due_date=now().date()),
        "upcoming_tasks": tasks.filter(due_date__gt=now().date())[:5],

        # chart data
        "step_labels": step_labels,
        "step_counts": step_counts,
        "status_labels": status_labels,
        "status_counts": status_counts,
    }

    return render(request, 'dashboard/liaison/liaison.html', context)



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
                create_notification(
                        recipient=request.user,
                        title="Employee registration Failed ",
                        message=f"{e}",
                        sender=request.user,
                        link=reverse('emplist'),
                        category="employee"
                    )

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




@login_required(login_url='/users/login')
def view_employee(request, emp_id):
    emp = get_object_or_404(Employee, id=emp_id)
    return render(request,'dashboard/admin/view_emp.html',{'employee': emp})

@login_required(login_url='/users/login')
def edit_profile(request):
    emp = Employee.objects.get(user=request.user)

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=emp)
        if form.is_valid():
            employee = form.save(commit=False)
            if 'profile_pic' in request.FILES:
                employee.profile_pic = request.FILES['profile_pic']

            employee.save()
            return redirect(view_profile)
    else:
        form = EmployeeForm(instance=emp)

    context = {
        'form': form,
        'employee': emp
    }
    return render(request,'dashboard/edit_profile.html', context)

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
    notification = get_object_or_404(
        Notification,
        id=nid,
        recipient=request.user
    )

    # mark as read
    if not notification.is_read:
        notification.is_read = True
        notification.save()

    # ✅ FIRST: check ?next= (used in dropdown)
    next_url = request.GET.get("next")
    if next_url:
        return redirect(next_url)

    # ✅ SECOND: fallback to notification link
    if notification.link:
        return redirect(notification.link)

    # ✅ FINAL fallback (same page)
    return redirect(request.META.get('HTTP_REFERER', 'notifications'))

@login_required(login_url='/users/login')
def mark_all_as_read(request):
    ntype = request.GET.get("type", "all")

    qs = Notification.objects.filter(recipient=request.user)

    if ntype == "unread":
        qs = qs.filter(is_read=False)
    elif ntype != "all":
        qs = qs.filter(category=ntype)

    qs.update(is_read=True)

    return redirect(request.META.get('HTTP_REFERER', 'notifications'))



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
def notifications(request):
    ntype = request.GET.get("type", "all")

    notifications_qs = Notification.objects.filter(
        recipient=request.user
    ).exclude(
        category__isnull=True
    ).exclude(
        category=''
    ).order_by('-created_at')

    categories = sorted(set(
        notifications_qs.values_list('category', flat=True)
    ))

    category_counts = dict(
        notifications_qs
        .values('category')
        .annotate(count=Count('id'))
        .values_list('category', 'count')
    )

    category_unread = dict(
        notifications_qs
        .filter(is_read=False)
        .values('category')
        .annotate(count=Count('id'))
        .values_list('category', 'count')
    )

    if ntype == "unread":
        filtered_qs = notifications_qs.filter(is_read=False)
    elif ntype != "all":
        filtered_qs = notifications_qs.filter(category=ntype)
    else:
        filtered_qs = notifications_qs

    paginator = Paginator(filtered_qs, 20)
    page = request.GET.get('page')
    notifications_page = paginator.get_page(page)

    CATEGORY_STYLES = {
        "project":  {"icon": "bi-briefcase-fill text-success", "badge": "bg-success"},
        "tasks":    {"icon": "bi-list-check text-primary", "badge": "bg-primary"},
        "material": {"icon": "bi-box-seam text-warning", "badge": "bg-warning text-dark"},
        "service":  {"icon": "bi-wrench-adjustable text-info", "badge": "bg-info text-dark"},
        "finance":  {"icon": "bi-cash-coin text-warning", "badge": "bg-warning text-dark"},
        "employee": {"icon": "bi-people-fill text-info", "badge": "bg-info text-dark"},
        "admin":    {"icon": "bi-bell-fill text-danger", "badge": "bg-danger"},
        "lead":     {"icon": "bi-person-plus-fill text-primary", "badge": "bg-primary"},
        "crm":      {"icon": "bi-person-lines-fill text-dark", "badge": "bg-dark"},
        "system":   {"icon": "bi-gear-fill text-secondary", "badge": "bg-secondary"},
    }

    for n in notifications_page:
        style = CATEGORY_STYLES.get(n.category, CATEGORY_STYLES["system"])
        n.icon = style["icon"]
        n.badge = style["badge"]

    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()

    return render(request, "dashboard/notifications.html", {
        "notifications": notifications_page,
        "ntype": ntype,
        "categories": categories,
        "category_counts": category_counts,
        "category_unread": category_unread,
        "unread_count": unread_count,
    })



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
    ntype = request.GET.get("type", "all")

    qs = Notification.objects.filter(recipient=request.user)

    if ntype == "unread":
        qs = qs.filter(is_read=False)
    elif ntype != "all":
        qs = qs.filter(category=ntype)

    qs.delete()

    return redirect(request.META.get('HTTP_REFERER', 'notifications'))


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
