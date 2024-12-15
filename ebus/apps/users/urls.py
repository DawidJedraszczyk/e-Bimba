from django.urls import path, include
from . import views
from django.utils.translation import gettext_lazy as _

app_name = 'users'

urlpatterns = [
    path('', views.UserDetail.as_view(), name='user_detail'),
    path('dostosuj-parametry/', views.UserMetricsUpdateView.as_view(), name='user_metrics'),
]
