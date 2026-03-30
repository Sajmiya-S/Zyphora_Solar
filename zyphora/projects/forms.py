from django import forms
from .models import *
from users.models import CustomUser


# ---------------- Project Forms ----------------
class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        exclude = ['slug', 'lead', 'created_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'project_type': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'revenue': forms.NumberInput(attrs={'class': 'form-control'}),
            'engineer': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['engineer'].queryset = Employee.objects.filter(user__role="engineer", is_active=True)


class ProjectActivityForm(forms.ModelForm):
    class Meta:
        model = ProjectActivity
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Activity title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Activity details'}),
        }


class ProjectMediaForm(forms.ModelForm):
    class Meta:
        model = ProjectMedia
        fields = ['project','file', 'caption', 'category', 'installation_task', 'work_report', 'service_report', 'issue']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'caption': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter a caption'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'installation_task': forms.Select(attrs={'class': 'form-select'}),
            'work_report': forms.Select(attrs={'class': 'form-select'}),
            'service_report': forms.Select(attrs={'class': 'form-select'}),
            'issue': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Get project from form data (POST) or initial value
        project_id = None
        if 'project' in self.data:
            project_id = self.data.get('project')
        elif 'project' in self.initial:
            project_id = self.initial.get('project')

        if self.user and 'installation_task' in self.fields:
            qs = self.fields['installation_task'].queryset.filter(assigned_to=self.user)
            if project_id:
                qs = qs.filter(project_id=project_id)
            self.fields['installation_task'].queryset = qs

        category = self.initial.get('category') or self.data.get('category')
        self.hide_fields_for_category(category)

    def hide_fields_for_category(self, category):
        if category == 'installation_photo':
            for field in ['work_report', 'service_report', 'issue']:
                self.fields[field].widget = forms.HiddenInput()
        elif category == 'issue_photo':
            for field in ['installation_task', 'work_report', 'service_report']:
                self.fields[field].widget = forms.HiddenInput()


# ---------------- Task Form ----------------
class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        exclude = ['status', 'created_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter task title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Task description'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'assigned_by': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['assigned_by'].initial = user
            self.fields['assigned_by'].widget = forms.HiddenInput()
            if not (user.is_superuser or user.role == "engineer"):
                self.fields.pop('assigned_to')
            else:
                self.fields['assigned_to'].queryset = CustomUser.objects.all()


# ---------------- Service Forms ----------------
class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['project', 'title', 'description', 'assigned_to']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service Title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Describe the service'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
        }


class ServiceReportForm(forms.ModelForm):
    class Meta:
        model = ServiceReport
        fields = ['report_text', 'images']
        widgets = {
            'report_text': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter service report details'}),
            'images': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


# ---------------- Installation Forms ----------------
class InstallationTaskForm(forms.ModelForm):
    class Meta:
        model = InstallationTask
        fields = ['step', 'status', 'notes']
        widgets = {
            'step': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }



class InstallationIssueForm(forms.ModelForm):
    class Meta:
        model = InstallationIssue
        fields = ['project', 'title', 'description', 'image']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short issue title (e.g., Panel crack)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the issue clearly...'}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }


# ---------------- Work Report ----------------
class WorkReportForm(forms.ModelForm):
    class Meta:
        model = WorkReport
        fields = [
            'project',
            'work_type',
            'title',
            'description',
            'status',
            'date',
            'before_image',
            'after_image',
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'work_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional title'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe the work done...'}),
            'before_image': forms.FileInput(attrs={'class': 'form-control'}),
            'after_image': forms.FileInput(attrs={'class': 'form-control'}),
        }