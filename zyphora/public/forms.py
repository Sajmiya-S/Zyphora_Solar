from django import forms
from .models import BlogPost



class BlogPostForm(forms.ModelForm):
    class Meta:
        model = BlogPost
        exclude = ['slug','published_date']
        widgets = {

            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter blog title...'
            }),

            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Short summary of the blog (leave empty to auto generate)'
            }),

            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 12,
                'placeholder': 'Write the blog content here...'
            }),

            'image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }


