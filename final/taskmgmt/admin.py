from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Project, Member, Task, Comment

User = get_user_model()

# 1. Define this helper once at the top of your admin.py file
def display_related(relation_name, attr='__str__', title=None):
    @admin.display(description=title or relation_name.replace('_', ' ').title())
    def _display(obj):
        rel = getattr(obj, relation_name, None)
        if rel:
            return ", ".join(str(getattr(item, attr, item)) for item in rel.all()) or "-"
        return "-"
    return _display

# Register your models here.
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username']

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'name', 
        'description',
        display_related('my_projects', attr='owner', title='Owner'),
        display_related('projects_joined', attr='members', title='Members'),
        'created_at'
                    ]

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['project', 'user', 'joined_at']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'description', 'status', 'due_date', 
                    display_related('tasks', attr='project', title='Related Project'),
                    display_related('assigned_tasks', attr='assigned_to', title='Assigned Users'),
                    display_related('created_tasks', attr='created_by', title='Created By'),
                    'created_at', 'updated_at']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['title', 'comment', 'task', 'user', 'date']