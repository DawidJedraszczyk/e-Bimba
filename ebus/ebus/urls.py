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
from django.views.i18n import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('route_search.urls', namespace='route_search')),
    path('gtfs-realtime', include('gtfs_realtime.urls', namespace='gtfs_realtime')),
    path('accounts/', include('allauth.urls')),
    path('użytkownik/', include('apps.users.urls')),
    path('zarejestruj/', SignupView.as_view(), name='account_signup'),
    path('zaloguj/', LoginView.as_view(), name='account_login'),
    path('wyloguj/', LogoutView.as_view(), name='account_logout'),
    path('zmień-hasło/', PasswordChangeView.as_view(), name='account_change_password'),
    path('resetuj-hasło/', PasswordResetView.as_view(), name='account_reset_password'),
    path('set_language/', set_language, name='set_language'),
]
