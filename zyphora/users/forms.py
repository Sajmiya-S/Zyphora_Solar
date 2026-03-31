from django import forms
from .models import *
import datetime


class EmployeeForm(forms.ModelForm):

    class Meta:
        model = Employee
        exclude = ['user', 'profile_pic']
        widgets = {
            'date_joined': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):

        role = kwargs.pop('role', None)   # ✅ remove role before super()
        super().__init__(*args, **kwargs)

        import datetime

        # Bootstrap styling
        for field in self.fields:
            if field != 'is_active':
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            else:
                self.fields[field].widget.attrs.update({'class': 'form-check-input'})

        # Default date
        if not self.instance.date_joined:
            self.fields['date_joined'].initial = datetime.date.today()

        # Hide fields based on role
        if role == 'engineer':
            self.fields['access_level'].widget = forms.HiddenInput()
            self.fields['supervisor'].widget = forms.HiddenInput()

        elif role == 'accountant':
            self.fields['specialization'].widget = forms.HiddenInput()
            self.fields['supervisor'].widget = forms.HiddenInput()

        elif role in ['sales', 'staff']:
            self.fields['specialization'].widget = forms.HiddenInput()
            self.fields['access_level'].widget = forms.HiddenInput()

        elif role == 'liaison':
            self.fields['specialization'].widget = forms.HiddenInput()
            self.fields['access_level'].widget = forms.HiddenInput()
            self.fields['supervisor'].widget = forms.HiddenInput()
        

class AdminProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            'first_name',
            'last_name',
            'username',
            'email'
        ]