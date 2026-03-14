from django.urls import path
from .views import *


urlpatterns = [ 
    path('review/',review_list,name='review'),
    path('approve-review/<int:rid>/',approve_review,name='approve_review'),
    path('delete-review/<int:rid>/',delete_review,name='delete_review'),
    path('leads/', lead_list, name='lead_list'),
    path('lead/<int:lid>/', view_lead, name='view_lead'),
    path('update-lead/<int:lid>/',update_lead, name='update_lead'),
    path('delete-lead/<int:lid>/', delete_lead, name='delete_lead'),
    path('add-lead/',add_lead,name='add_lead'),
    path('followup/<int:lid>/',mark_followup_done,name='mark_followup_done'),
    path('sitevisit/<int:lid>/',mark_site_visit_done,name='mark_site_visit_done'),

]