from django.views.generic import DetailView, UpdateView

from .forms import UserMetricsForm
from .models import User
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.core.paginator import Paginator

class UsersMixin(LoginRequiredMixin):
    login_url = reverse_lazy('account_login')

class UserDetail(LoginRequiredMixin, DetailView):
    template_name = 'users/user_detail.html'
    context_object_name = 'user'

    def get_object(self, queryset=None):
        return self.request.user

class UserMetricsUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserMetricsForm
    template_name = 'users/user_metrics_form.html'

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        return reverse_lazy('users:user_detail')