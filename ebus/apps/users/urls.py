from django.urls import path, include
from . import views
from django.utils.translation import gettext_lazy as _

app_name = 'users'

urlpatterns = [
    # User detail view
    path('', views.UserDetail.as_view(), name='user_detail'),

    # User metrics update view
    path(_('adjust-parameters/'), views.UserMetricsUpdateView.as_view(), name='user_metrics'),
]
