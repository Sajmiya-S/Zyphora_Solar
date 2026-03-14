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
    path('update-caption/<int:id>/',update_image_caption,name='update_caption')
]