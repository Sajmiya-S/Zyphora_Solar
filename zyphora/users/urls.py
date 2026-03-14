from django.urls import path
from .views import *



urlpatterns = [
    path('login/',login_page,name='login'),
    path('logout/',logout_page,name='logout'),
    path('dashboard/',dashboard,name='dashboard'),
    path('admin/',admin_dashboard,name='admin'),
    path('engineer/',engineer_dashboard,name='engineer'),
    path('accountant/',accountant_dashboard,name='accountant'),
    path('sales/',sales_dashboard,name='sales'),
    path('staff/',staff_dashboard,name='staff'),
    path('addemp/',add_employee,name='addemp'),
    path('change-password/',ChangePassword.as_view(),name='password'),
    path('emplist/',all_employees,name='emplist'),
    path('view-emp/<int:emp_id>/',view_employee,name='viewemp'),
    path('edit-emp/<int:emp_id>/',edit_employee,name='editemp'),
    path('profile/',view_profile,name='profile'),
    path('blog/',blog_list,name='blogposts'),
    path('add-post/',add_post,name='addpost'),
    path('view-post/<int:id>/',view_post,name='viewpost'),
    path('edit-post/<int:bid>/',edit_post,name='editpost'),
    path('delete-post/<int:bid>/',delete_post,name='deletepost'),
    path('mark-as-read/<int:nid>/', mark_as_read, name='mark_as_read'),
    path('mark-all-as-read/', mark_all_as_read, name='mark_all_as_read'),
    path('notification-data/',get_notifications,name='notification_data'),
    path('notifications/<str:ntype>', notifications, name='notifications'),
    path('delete-notification/<int:nid>/',delete_notification,name='delete_notification'),
    path('delete-all-notifications/', delete_all_notifications, name='delete_all_notifications'),
    path('notify/<int:id>/',notifyEmployee,name='notify')

]