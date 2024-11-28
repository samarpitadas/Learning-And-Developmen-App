from django.contrib import admin
from django.urls import path, include
from authenticate import views
from django.urls import path, include
from django.contrib.auth import views as auth_views
   

urlpatterns = [
    path('api/register/', views.register_user, name='register'),
    path('api/login/', views.login_user, name='login'),
    path('api/logout/', views.logout_user, name='logout'),
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('authenticate.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='accounts_login'),
    path('api/view-requests/', views.view_requests, name='view_requests'),
    path('api/my-progress/', views.my_progress_view, name='my_progress'),
]

