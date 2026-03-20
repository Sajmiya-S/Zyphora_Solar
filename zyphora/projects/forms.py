from django import forms

from .models import *

from users.models import CustomUser


class ProjectForm(forms.ModelForm):

    class Meta:
        model = Project
        exclude = ['slug','lead','created_at','updated_at']

        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control'}),
            'project_type': forms.Select(attrs={'class':'form-control'}),
            'description': forms.Textarea(attrs={'class':'form-control'}),
            'location': forms.TextInput(attrs={'class':'form-control'}),
            'revenue': forms.NumberInput(attrs={'class':'form-control'}),
            'start_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'end_date': forms.DateInput(attrs={'type':'date','class':'form-control'}),
            'status': forms.Select(attrs={'class':'form-control'}),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.fields['engineer'].queryset = CustomUser.objects.filter(role="engineer", is_active=True)

class ProjectImageForm(forms.ModelForm):

    class Meta:
        model = ProjectImage
        fields = ['image','caption']

        widgets = {
            'image': forms.ClearableFileInput(attrs={'class':'form-control'}),
            'caption': forms.TextInput(attrs={'class':'form-control'})
        }





class ProjectActivityForm(forms.ModelForm):

    class Meta:
        model = ProjectActivity
        fields = ['title','description']

        widgets = {
            'title': forms.TextInput(attrs={
                'class':'form-control',
                'placeholder':'Activity title'
            }),
            'description': forms.Textarea(attrs={
                'class':'form-control',
                'rows':4,
                'placeholder':'Activity details'
            })
        }


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        exclude = ['status','created_at']

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter task title'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Task description'
            }),

            'assigned_to': forms.Select(attrs={
                'class': 'form-select'
            }),

            'assigned_by': forms.Select(attrs={
                'class': 'form-select'
            }),

            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    def __init__(self, *args, **kwargs):

        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:

            # Assigned by = current user
            self.fields['assigned_by'].initial = user
            self.fields['assigned_by'].widget = forms.HiddenInput()

            # Normal users cannot assign tasks
            if not (user.is_superuser or user.role == "engineer"):

                # remove field completely
                self.fields.pop('assigned_to')

            else:
                # Admin and Engineer can assign to anyone INCLUDING themselves
                self.fields['assigned_to'].queryset = CustomUser.objects.all()


class ServiceRequestForm(forms.ModelForm):
    class Meta:
        model = ServiceRequest
        fields = ['project','title', 'description', 'assigned_to', ]
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