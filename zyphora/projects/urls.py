from django.urls import path
from .views import *



urlpatterns = [
    path('all-projects/',all_projects,name='project_list'),
    path('edit-project/<int:pid>/',update_project,name='edit_project'),
    path('view-project/<int:pid>/',view_project,name='project_detail'),


    path('delete-image/<int:id>/',delete_project_image,name='delete_image'),
    path('add-image/<int:pid>/',add_project_images,name='add_images'),


    path('activities/<int:pid>/', project_activities, name='project_activities'),
    path('recent-activity',recent_activity,name='recent_activity'),
    path('add-activity/<int:pid>/',add_activity,name='add_activity'),


    path('project-gallery/<int:pid>/',project_gallery,name='project_gallery'),
    path('gallery-projects/',gallery_projects,name='gallery_projects'),
    path('update-caption/<int:id>/',update_image_caption,name='update_caption'),



    path('my-tasks',my_tasks,name='my_tasks'),
    path('assigned-tasks',assigned_tasks,name='assigned_tasks'),
    path('create-task',create_task,name='create_task'),
    path('complete-tasks/<int:id>/', complete_task, name='complete_task'),
    path('edit-tasks/<int:id>/', edit_task, name='edit_task'),
    path('delete-tasks/<int:id>/', delete_task, name='delete_task'),
    
    
    path('progress',installation_progress,name='progress'),

    path('design',design_list,name='design_list'),
    path('design-detail/<int:pid>/',design_detail,name='design_detail'),


    path('assigned-service/', assigned_service_requests, name='assigned_service_requests'),
    path('add-service/', add_service_request, name='add_service_request'),
    path('service-history/', service_history, name='service_history'),
    path('service-report/', add_service_report, name='add_service_report'),
    path('service-reports/', service_reports, name='service_reports'),

    path('service-requests/', service_requests, name='service_requests'),
    path('redirect-service-requests/<int:pk>/', redirect_service_request, name='redirect_service_request'),

    path('installation-tasks/',installation_tasks,name='installation_tasks'),
    path('staff-projects/',staff_projects,name='staff_projects'),
]