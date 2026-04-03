from django.urls import path
from .views import *


urlpatterns = [ 
    path('review/',review_list,name='review'),
    path('delete-review/<int:rid>/',delete_review,name='delete_review'),

    path('leads/', lead_list, name='lead_list'),
    path('lead/<int:lid>/', view_lead, name='view_lead'),
    path('update-lead/<int:lid>/',update_lead, name='update_lead'),
    path('delete-lead/<int:lid>/', delete_lead, name='delete_lead'),
    path('add-lead/',add_lead,name='add_lead'),

    path('mark-sitevisit/<int:vid>/',mark_site_visit_done,name='mark_site_visit_done'),
    path('sitevisits/<str:filter>/',site_visits,name='site_visits'),
    path('edit-visit/<int:vid>/',edit_site_visit,name='edit_visit'),
    path('site-photo/',upload_site_photos_page,name='upload_site_photos'),
    
    path('mark-followup/<int:fid>/',mark_followup_done,name='mark_followup_done'),
    path('followups/',follow_ups,name='followups'),
    path('edit-followup/<int:fid>/',edit_followup,name='edit_followup'),

]