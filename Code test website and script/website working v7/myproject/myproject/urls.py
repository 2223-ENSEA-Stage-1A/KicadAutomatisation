"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from myapp import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf import settings
from django.conf.urls.static import static

from myapp.views import home, logged_home, profile, user_files, delete_file, file_explorer_view, download_file_view

from django.contrib.auth.views import LogoutView

from django.urls import path, include
import django_cas_ng.views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('gerber-upload/', views.gerber_upload, name='gerber_upload'),
    path('accounts/profile/', profile, name='profile'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('logged_home/', logged_home, name='logged_home'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),

    path('accounts/login', django_cas_ng.views.LoginView.as_view(), name='cas_ng_login'),
    path('accounts/logout', django_cas_ng.views.LogoutView.as_view(), name='cas_ng_logout'),

    path('user-files/', user_files, name='user_files'),

    path('delete_file/', delete_file, name='delete_file'),
    path('delete_file/<int:file_id>/', views.delete_file, name='delete_file'),

    path('view_file/<int:file_id>/<str:file_type>/', views.view_file, name='view_file'),

    path('run_script', views.run_script, name='run_script'),

    path('file-explorer/', file_explorer_view, name='file_explorer'),

    path('download-file/', download_file_view, name='download_file'),

    
    
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

