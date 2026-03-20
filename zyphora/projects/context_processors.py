from .models import Task
from datetime import date

def task_processor(request):
    pending = 0
    overdue = 0
    todays = 0

    if request.user.is_authenticated:
        today = date.today()

        tasks = Task.objects.filter(assigned_to=request.user)

        pending = tasks.filter(status='in_progress').count()
        overdue = tasks.filter(status='pending', due_date__lt=today).count()
        todays = tasks.filter(status='pending', due_date=today).count()

    context = {
        'pending': pending,
        'overdue': overdue,
        'todays': todays
    }

    return context