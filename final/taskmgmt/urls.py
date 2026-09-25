from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.Register.as_view(), name='register'),
    path('login/', views.Login.as_view(), name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('users/myprofile/', views.Users.as_view(http_method_names=['get', 'patch']), name='myuser'),
    path('users/changepassword/', views.Users.as_view(http_method_names=['post']), name='changepassword'),
    path('users/myprofile/delete/', views.Users.as_view(http_method_names=['delete']), name='deletemyuser'),
    path('users/', views.Admin.as_view(http_method_names=['get']), name='allusers'),
    path('users/<uuid:id>/', views.Admin.as_view(http_method_names=['delete']), name='deleteanyuser'),
    path('projects/', views.ProjectView.as_view(http_method_names=['get']), name='belonging_projects'),
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
    path('projects/<int:pk>/tasks/comments/', views.Comments.as_view(http_method_names=['get']), name='view_comments'),
    path('projects/<int:pk>/tasks/<int:pkt>/comment/', views.Comments.as_view(http_method_names=['post']), name='comment_on_task'),
    path('projects/tasks/comments/', views.AdminProject.as_view(), name='view_projects,_tasks_and_comments'),
]