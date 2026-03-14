from django import forms
from datetime import date

from .models import Review,Lead


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        exclude = ['created_at', 'rating','is_approved']  
        labels = {
            'name': '',
            'email': '',
            'review': '',
            'location':''
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your Email'}),
            'location': forms.TextInput(attrs={'placeholder':'Your Location'}),
            'review': forms.Textarea(attrs={'placeholder': 'Write your review ...', 'rows':4}),
        }
from django import forms
from .models import Lead

class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['name','phone','email','location','service','message']

        labels = {
            'name': '',
            'phone': '',
            'email': '',
            'location': '',
            'service': '',
            'message': '',
            
        }

        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Full name',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'Phone number',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email address',
                'class': 'form-control'
            }),
            'service': forms.Select(attrs={
                'class': 'form-select'
            }),
            'message': forms.Textarea(attrs={
                'placeholder': 'Your message here',
                'rows':4,
                'class':'form-control'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Your address or landmark',
                'class':'form-control'
            })
        }


class LeadUpdateForm(forms.ModelForm):

    class Meta:
        model = Lead
        fields = [
            'status',
            'priority',
            'assigned_to',
            'site_visit_date',
            'follow_up_date',
            'notes'
        ]

        widgets = {

            'status': forms.Select(attrs={'class':'form-select'}),

            'priority': forms.Select(attrs={'class':'form-select'}),

            'assigned_to': forms.Select(attrs={'class':'form-select'}),

            'site_visit_date': forms.DateInput(attrs={
                'type':'date',
                'class':'form-control'
            }),

            'follow_up_date': forms.DateInput(attrs={
                'type':'date',
                'class':'form-control',
                'min': date.today().isoformat()
            }),

            'notes': forms.Textarea(attrs={
                'rows':4,
                'class':'form-control',
                'placeholder':'Add internal notes...'
            })
        }

    