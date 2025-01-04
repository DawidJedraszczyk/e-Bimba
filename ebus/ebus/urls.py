from django.contrib import admin
from django.urls import path, include
from allauth.account.views import SignupView, LoginView, LogoutView, PasswordChangeView, PasswordResetView
from django.conf import settings
from django.conf.urls.static import static
from django.utils.translation import gettext_lazy as _
from django.conf.urls.i18n import i18n_patterns

from apps import feedback

# Translated URL patterns
urlpatterns = i18n_patterns(
    # Authentication views with translated paths
    path(_('signup/'), SignupView.as_view(), name='account_signup'),
    path(_('login/'), LoginView.as_view(), name='account_login'),
    path(_('logout/'), LogoutView.as_view(), name='account_logout'),
    path(_('change-password/'), PasswordChangeView.as_view(), name='account_change_password'),
    path(_('reset-password/'), PasswordResetView.as_view(), name='account_reset_password'),

    # Allauth and User-specific routes
    path(_('accounts/'), include('allauth.urls')),
    path(_('user/'), include('apps.users.urls')),

    # Tickets module
    path(_('tickets/'), include('tickets.urls')),
)

# Non-translated URL patterns
urlpatterns += [
    # Admin site
    path('admin/', admin.site.urls),

    # Route Search App
    path('', include('route_search.urls', namespace='route_search')),
    path('feedback/', include('feedback.urls', namespace='feedback')),

    # GTFS Realtime Integration
    path('gtfs-realtime/', include('gtfs_realtime.urls', namespace='gtfs_realtime')),

    # Language settings
    path("i18n/", include("django.conf.urls.i18n")),
]
