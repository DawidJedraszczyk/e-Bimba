from django.urls import path
from . import views
from rest_framework.urlpatterns import format_suffix_patterns


app_name = 'feedback'

urlpatterns = [
    path('create', views.FeedbackCreateApiView.as_view(), name='create-feedback'),
]

urlpatterns = format_suffix_patterns(urlpatterns)