from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.Register.as_view(), name='register'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('projects/', views.ProjectView.as_view(http_method_names=['get']), name='all_projects'),
    path('projects/create/', views.ProjectView.as_view(http_method_names=['post']), name='create_project'),
    path('projects/update/<int:pk>/', views.ProjectView.as_view(http_method_names=['patch']), name='update_project'),
    path('projects/delete/<int:pk>/', views.ProjectView.as_view(http_method_names=['delete']), name='delete_project')
]