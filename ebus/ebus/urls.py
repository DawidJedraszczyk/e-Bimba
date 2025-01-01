"""
URL configuration for ebus project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from allauth.account.views import SignupView, LoginView, LogoutView, PasswordChangeView, PasswordResetView
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import set_language
from django.utils.translation import gettext_lazy as _

urlpatterns = [
    # Admin site
    path('admin/', admin.site.urls),

    # Route Search App
    path('', include('route_search.urls', namespace='route_search')),

    # GTFS Realtime Integration
    path('gtfs-realtime/', include('gtfs_realtime.urls', namespace='gtfs_realtime')),

    # User Authentication (Allauth)
    path(_('accounts/'), include('allauth.urls')),

    # User-specific routes
    path(_('user/'), include('apps.users.urls')),

    # Tickets module
    path(_('tickets/'), include('tickets.urls')),

    # Authentication views with translated paths
    path(_('signup/'), SignupView.as_view(), name='account_signup'),
    path(_('login/'), LoginView.as_view(), name='account_login'),
    path(_('logout/'), LogoutView.as_view(), name='account_logout'),
    path(_('change-password/'), PasswordChangeView.as_view(), name='account_change_password'),
    path(_('reset-password/'), PasswordResetView.as_view(), name='account_reset_password'),

    # Language settings
    path('set_language/', set_language, name='set_language'),
    path("i18n/", include("django.conf.urls.i18n")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)