from django.urls import path
from django.conf.urls.static import static
from django.contrib.auth import settings
from .views import *

urlpatterns = [
    path('',home_page,name='home'),
    path('about/',about_page,name='about'),
    path('services/',services_page,name='services'),
    path('projects/',projects_page,name='projects'),
    path('contact/',contact_page,name='contact'),
    path('save/',savings_calculator,name='save'),
    path('blog/',blog_list,name='blog'),
    path('blog/<slug:slug>/', blog_detail, name='blog_detail'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)