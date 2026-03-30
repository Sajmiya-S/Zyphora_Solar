from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db.models import Avg

from .models import WorkReport
from users.models import CustomUser


@shared_task
def generate_weekly_reports():
    today = timezone.now().date()
    start_date = today - timedelta(days=7)

    users = CustomUser.objects.all()

    for user in users:
        # Get all daily reports in last 7 days
        reports = WorkReport.objects.filter(
            user=user,
            report_type='daily',
            date__range=[start_date, today]
        )

        if not reports.exists():
            continue

        # Group by project
        projects = reports.values_list('project', flat=True).distinct()

        for project_id in projects:
            project_reports = reports.filter(project_id=project_id)

            # Skip if weekly already exists for this week
            if WorkReport.objects.filter(
                user=user,
                project_id=project_id,
                report_type='weekly',
                date=today
            ).exists():
                continue

            # Generate summary
            descriptions = project_reports.values_list('description', flat=True)
            combined_description = "\n".join(descriptions)

            avg_progress = project_reports.aggregate(avg=Avg('progress'))['avg'] or 0

            # Create weekly report
            WorkReport.objects.create(
                user=user,
                project_id=project_id,
                report_type='weekly',
                work_type='other',
                title=f"Weekly Report ({start_date} to {today})",
                description=combined_description,
                date=today,
                status='completed' if avg_progress == 100 else 'in_progress',
                progress=int(avg_progress)
            )