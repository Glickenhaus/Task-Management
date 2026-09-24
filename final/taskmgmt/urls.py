from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.Register.as_view(), name='register'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('projects/', views.ProjectView.as_view(http_method_names=['get']), name='all_projects'),
    path('projects/create/', views.ProjectView.as_view(http_method_names=['post']), name='create_project'),
    path('projects/<int:pk>/update/', views.ProjectView.as_view(http_method_names=['patch']), name='update_project'),
    path('projects/<int:pk>/delete/', views.ProjectView.as_view(http_method_names=['delete']), name='delete_project'),
    path('projects/<int:pk>/members/', views.AddMember.as_view(http_method_names=['get']), name='view_project_members'),
    path('projects/<int:pk>/members/add/', views.AddMember.as_view(http_method_names=['post']), name='add_members'),
    path('projects/<int:pk>/members/remove/', views.RemoveMember.as_view(http_method_names=['post']), name='remove_members'),
    path('projects/<int:pk>/members/role/', views.RoleChange.as_view(), name='change_member_role'),
    path('projects/<int:pk>/tasks/', views.Tasks.as_view(http_method_names=['get']), name='project_tasks'),
    path('projects/<int:pk>/tasks/create/', views.Tasks.as_view(http_method_names=['post']), name='create_task'),
    path('projects/<int:pk>/tasks/<int:pkt>/update/', views.Tasks.as_view(http_method_names=['patch']), name='update_task'),
    path('projects/<int:pk>/tasks/<int:pkt>/delete/', views.Tasks.as_view(http_method_names=['delete']), name='delete_task'),
]