from django import forms
from .models import Project, ProjectImage, ProjectActivity


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