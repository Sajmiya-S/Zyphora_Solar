from django import forms
from datetime import date

from .models import *


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
            'notes'
        ]

        widgets = {
            'status': forms.Select(attrs={'class':'form-select'}),
            'priority': forms.Select(attrs={'class':'form-select'}),
            'assigned_to': forms.Select(attrs={'class':'form-select'}),
            'notes': forms.Textarea(attrs={
                'rows':4,
                'class':'form-control',
                'placeholder':'Add internal notes...'
            })
        }


class SiteVisitForm(forms.ModelForm):
    class Meta:
        model = SiteVisit
        fields = ['scheduled_date','engineer','notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={
                'type':'date',
                'class':'form-control',
                'min': date.today().isoformat()
            }),
            'notes': forms.Textarea(attrs={
                'rows':3,
                'class':'form-control',
                'placeholder':'Add site visit notes...'
            }),
            'engineer': forms.Select(attrs={'class':'form-select'}),
        }

class UpdateVisitForm(forms.ModelForm):
    class Meta:
        model = SiteVisit
        fields = ['completed_date','notes','status']
        widgets = {
            'completed_date': forms.DateInput(attrs={
                'type':'date',
                'class':'form-control',
                'min': date.today().isoformat()
            }),
            'notes': forms.Textarea(attrs={
                'rows':3,
                'class':'form-control',
                'placeholder':'Add site visit notes...'
            }),
            'status': forms.Select(attrs={'class':'form-select'}),
        }

# ---------------- Upload Photos for Site Visit ----------------
class SitePhotoForm(forms.ModelForm):
    class Meta:
        model = SitePhoto
        fields = ['visit', 'photo']
        widgets = {
            'visit': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'})  # single file only
        }



class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['scheduled_date', 'note']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={
                'type':'date',
                'class':'form-control',
                'min': date.today().isoformat()
            }),
            'note': forms.Textarea(attrs={
                'rows':3,
                'class':'form-control',
                'placeholder':'Add follow-up note...'
            }),
        }