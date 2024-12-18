from django import forms
from .models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.utils.translation import gettext_lazy as _

class UserMetricsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['pace', 'max_distance']
