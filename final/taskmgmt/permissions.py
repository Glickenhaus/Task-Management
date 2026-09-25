from rest_framework import permissions
from .models import Project, Member, Task

class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True
        project = obj if isinstance(obj, Project) else obj.project
        return Member.objects.filter(project=project, user=request.user, role=Member.Role.OWNER).exists()

class IsOwnerOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True
        project = obj if isinstance(obj, Project) else obj.project
        member = Member.objects.filter(project=project, user=request.user).first()
        if not member:
            return False
        return member.role in [Member.Role.OWNER, Member.Role.ADMIN]

class CanManageTask(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True
        if not isinstance(obj, Task):
            return False
        member = Member.objects.filter(project=obj.project, user=request.user).first()
        if not member:
            return False
        if member.role in [Member.Role.OWNER, Member.Role.ADMIN]:
            return True
        if obj.assigned_to == request.user:
            if request.method == 'DELETE':
                return False
            return True
        return request.method in permissions.SAFE_METHODS

class IsMember(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_superuser:
            return True
        project = obj if isinstance(obj, Project) else obj.project
        return Member.objects.filter(project=project, user=request.user).exists()



