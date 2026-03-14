from django.shortcuts import render,redirect
from django.contrib import messages
from django.urls import reverse
from users.utils import create_notification


from .models import BlogPost 

from crm.models import LeadActivity,Review
from crm.forms import ReviewForm,LeadForm

from users.models import Notification,CustomUser


def home_page(request):
    reviews = Review.objects.filter(is_approved=True).order_by('-created_at')[:8]
    if request.method == "POST":
        form = ReviewForm(request.POST)
        rating = request.POST.get('rating') 

        if form.is_valid() and rating:
            review = form.save(commit=False)
            review.rating = rating 
            review.save()  
            messages.success(request,"🎉 Thank you! Your review has been submitted successfully.")
            admin = CustomUser.objects.get(role='admin')
            Notification.objects.create(
                recipient=admin,
                message=f"New review received from {review.name}",
                link = reverse('notifications',kwargs={'ntype':'all'}),
                category='crm'
                )
    form = ReviewForm()
    return render(request,'public_view/home.html',{'reviews':reviews,'form':form})

def about_page(request):
    return render(request,'public_view/about.html')

def services_page(request):
    return render(request,'public_view/services.html')

def contact_page(request):
    if request.method == "POST":
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save()
            LeadActivity.objects.create(
                lead=lead,
                title="Lead Created",
                description="Lead submitted from website contact form"
            )
            admin = CustomUser.objects.get(role='admin')
            create_notification(
                recipient=admin,
                title="New Lead Added",
                message=f"{lead.name} has been added from website contact form",
                link=reverse('notifications',kwargs={'ntype':'all'}),
                category='crm'
            )
        messages.success(request,'Thank you for requesting a free consultation! Our representative will reach out to you shortly to assist you.')
        return redirect(contact_page)
    form = LeadForm()
    return render(request,'public_view/contact.html',{'form':form})

def projects_page(request):
    return render(request,'public_view/projects.html')

def savings_calculator(request):
    default_tariff = 7  # Kerala average ₹/kWh
    savings = None
    if request.method == "POST":
        try:
            monthly_bill = float(request.POST.get('monthly_bill'))
            system_size = float(request.POST.get('system_size'))
            tariff = float(request.POST.get('tariff', default_tariff))

            monthly_generation = 4 * 30 * system_size
            current_usage = monthly_bill / tariff
            savings_kwh = min(monthly_generation, current_usage)
            savings = round(savings_kwh * tariff * 12)

        except Exception as e:
            savings = None

    return render(request,'public_view/savings_calculator.html',{"savings": savings, "default_tariff": default_tariff})


def blog_list(request):
    posts = BlogPost.objects.order_by('-published_date')
    return render(request, 'public_view/blog.html', {'blog_posts': posts})



def blog_detail(request, slug):
    post = BlogPost.objects.get(slug=slug)
    return render(request, 'public_view/blog_detail.html', {'post': post})

