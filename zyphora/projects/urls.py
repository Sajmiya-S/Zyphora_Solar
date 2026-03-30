from django.urls import path
from .views import *



urlpatterns = [
    path('all-projects/',all_projects,name='project_list'),
    path('completed-projects/',completed_projects,name='completed_projects'),
    path('completed-project/<int:pid>/',completed_project_detail,name='completed_project_detail'), 
    path('edit-project/<int:pid>/',update_project,name='edit_project'),
    path('view-project/<int:pid>/',view_project,name='project_detail'),


    path('delete-media/<int:id>/',delete_project_media,name='delete_media'),
    path('add-media/<int:pid>/',add_project_media,name='add_media'),


    path('activities/<int:pid>/', project_activities, name='project_activities'),
    path('recent-activity',recent_activity,name='recent_activity'),
    path('add-activity/<int:pid>/',add_activity,name='add_activity'),


    path('project-gallery/<int:pid>/',project_gallery,name='project_gallery'),
    path('gallery-projects/',gallery_projects,name='gallery_projects'),
    path('update-caption/<int:id>/',update_caption,name='update_caption'),



    path('my-tasks',my_tasks,name='my_tasks'),
    path('assigned-tasks',assigned_tasks,name='assigned_tasks'),
    path('create-task',create_task,name='create_task'),
    path('complete-tasks/<int:id>/', complete_task, name='complete_task'),
    path('edit-tasks/<int:id>/', edit_task, name='edit_task'),
    path('delete-tasks/<int:id>/', delete_task, name='delete_task'),
    
    path('feasibility',feasibility_list,name='feasibility_list'),
    path('create_feasibility/', create_feasibility_general, name='create_feasibility_general'),
    path('create_feasibility/<int:pid>/', create_feasibility, name='create_feasibility'),
    path('feasibility/<int:fid>/', feasibility_detail, name='feasibility_detail'),
    path('approve-feasibility/<int:fid>/', approve_feasibility, name='approve_feasibility'),
    path('reject-feasibility/<int:fid>/', reject_feasibility, name='reject_feasibility'),

    path('progress',installation_progress,name='installation_progress'),

    path('design',design_list,name='design_list'),
    path('design-detail/<int:pid>/',design_detail,name='design_detail'),
    path('delete-design/<int:doc_id>/', delete_design_file, name='delete_design_file'),

    path('all_layouts/',view_project_layouts,name='layouts'),
    path('layout/<int:pid>/',project_layout_detail,name='project_layout'),


    path('assigned-service/', assigned_service_requests, name='assigned_service_requests'),
    path('add-service/', add_service_request, name='add_service_request'),
    path('service-history/', service_history, name='service_history'),
    path('service-report/<int:rid>/', add_service_report, name='add_service_report'),
    path('service-report-detail/<int:rid>/', service_report_detail, name='service_report_detail'),
    path('service-reports/', service_reports, name='service_reports'),

    path('service-requests/', service_requests, name='service_requests'),
    path('redirect-service-requests/<int:pk>/', redirect_service_request, name='redirect_service_request'),

    path('installation-tasks/',installation_tasks,name='installation_tasks'),

    path('work-progress/', update_work_progress, name='update_work_progress'),
    path('upload-photos/', upload_photos, name='upload_photos'),
    path('get-project-photos/', get_project_photos, name='get_project_photos'),
    path('report-issues/', report_issues, name='report_issues'),

    path('reports/', daily_report_list, name='daily_report_list'),
    path('reports/create/', create_daily_report, name='create_daily_report'),
    path('reports/<int:pk>/', daily_report_detail, name='daily_report_detail'),
    path('weekly-reports/', weekly_report_list, name='weekly_report_list'),
    path('weekly-reports/<int:pk>/', weekly_report_detail, name='weekly_report_detail'),    
    path('project-reports/', completion_report_list, name='completion_report_list'),
    path('project-reports/<int:pk>/', completion_report_detail, name='completion_report_detail'),
    path('create-report/', create_completion_report, name='create_completion_report'),
    path('download-report/<str:type>/', download_report, name='download_report'),
    path('download-report/<str:type>/<int:id>/', download_report, name='download_report'),

    path('licensing/',licensing_list,name='licensing_list'),
    path('licensing/<int:id>/', licensing_dashboard, name='licensing_dashboard'),
    path('complete-licensing-task/<int:id>/complete/', complete_licensing_task, name='complete_licensing_task'),
    path('licensing-phase/<str:phase>/', licensing_by_phase, name='licensing_by_phase'),

    path('energisation/', energisation_projects, name='energisation_projects'),
    path('project-completed/<int:id>/', mark_project_completed, name='mark_project_completed'),

]