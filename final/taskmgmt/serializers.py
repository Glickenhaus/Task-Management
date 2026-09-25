from rest_framework import serializers
from django.contrib.auth import get_user_model
from .validators import validate_email
from .models import Project, Member, Task, Comment
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.CharField(required=True, validators=[validate_email])
    password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def validate_username(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Username must be at least 8 characters.")
        return value

    def validate_password(self, value):
        username = self.initial_data.get('username')
        email = self.initial_data.get('email')
        user = User(email=email, username=username)

        try:
            validate_password(value, user=user)
        except ValueError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password= serializers.CharField(required=True, write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Your old password was entered incorrectly.")
        return value

    def validate(self, attrs):
        if attrs['old_password'] == attrs('new_password'):
            raise serializers.ValidationError[{"new_password": "Your old and new password cannot be the same."}]       
        return attrs

class LoginSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)
        access_token = refresh.access_token
  
        data['user'] = {
            'id': str(self.user.id),
            'username': str(self.user.username),
            'email': str(self.user.email),
        }
        data['created'] = access_token.get('iat')
        data['expiry'] = access_token.get('exp')

        return data

class ProjectSerializer(serializers.ModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    # Pulls just the 'username' string from each member in the project
    members = serializers.SlugRelatedField(many=True, read_only=True, slug_field='username')

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'owner', 'members', 'created_at']
        read_only_fields = ['id', 'owner', 'created_at']

class TaskSerializer(serializers.ModelSerializer):
    project = serializers.SlugRelatedField(slug_field='name', read_only=True)
    assigned_to = serializers.SlugRelatedField(required=False, slug_field='username', queryset=User.objects.all())
    created_by = serializers.SlugRelatedField(read_only=True, slug_field='username')

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'due_date', 'project', 'assigned_to', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Enforce Rule: Only members of the project can be assigned tasks.
        # Handles both creation (POST) and partial updates (PATCH).
        
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        if user and user.is_superuser:
            return attrs
        
        # Determine the project (from payload or existing instance)
        project = self.context.get('project', getattr(self.instance, 'project', None))

        # Determine the assignee (from payload or existing instance)
        assigned_to = attrs.get('assigned_to', getattr(self.instance, 'assigned_to', None))

        restricted_fields = ['title', 'description', 'due_date', 'assigned_to']

        if project:
            member = Member.objects.filter(project=project, user=user).first()
            if user and not member:
                raise serializers.ValidationError({"project": f"You must be a member of {project.name} to create or modify its tasks."})
            
            # Get the role of the one making the request
            role = member.role

            if assigned_to and not project.members.filter(id=assigned_to.id).exists():
                raise serializers.ValidationError({"assigned_to": f"User {assigned_to.username} is not a member of project {project.name}."})

            if user and role == 'MEMBER' and assigned_to != user:
                raise serializers.ValidationError({"assigned_to": "Only admins or owners can assign tasks to others."})

        restricted = []
        if self.instance:
            task = self.context.get('task', getattr(self.instance, 'task', None))
            if project and task.project != project:
                raise serializers.ValidationError({"task": f"Task {task.id} is not associated with project {project.name}."})
        
            if 'project' in attrs and not user.is_superuser:
                raise serializers.ValidationError("You can not change this task's project.")
            
            for field in restricted_fields:
                if field in attrs and role == Member.Role.MEMBER:
                    restricted.append(field)
            if restricted:
                raise serializers.ValidationError(f"You do not have permission to modify {restricted}.")     

        return attrs

class RoleSerializer(serializers.ModelSerializer):
    # 1. Accept username in payload for identification, but mark read_only so DRF doesn't try to write/update it on the User model.
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Member
        fields = ['username', 'role']

    def validate_role(self, value):
        request = self.context.get('request')

        if request.user and request.user.is_superuser:
            return value
        
        project = self.instance.project
        member = Member.objects.filter(project=project, user=request.user).first()

        # Get the role of the one making the request
        role = member.role

        if self.instance:
            if self.instance.role == 'ADMIN' and role != 'OWNER':
                raise serializers.ValidationError("Only owners can change an admin's role.")
            if self.instance.role == 'OWNER':
                raise serializers.ValidationError("Owner's role can not be changed.")
            if self.instance.role in [Member.Role.ADMIN, Member.Role.MEMBER] and value == 'OWNER':
                raise serializers.ValidationError("There can only be one owner per project.")

        return value

class CommentSerializer(serializers.ModelSerializer):
    task = serializers.SlugRelatedField(read_only=True, slug_field='title')
    user = serializers.ReadOnlyField(source='user.username')
    
    class Meta:
        model = Comment
        fields = ['id', 'title', 'comment', 'task', 'user', 'date']
        read_only_fields = ['id', 'date']

    def validate(self, attrs):

        request = self.context.get('request')
        user = request.user

        if user and user.is_superuser:
            return attrs

        project = self.context.get('project', getattr(self.instance, 'project', None))
        task = self.context.get('task', getattr(self.instance, 'task', None))
        comment = attrs.get('comment')

        # Query DB to prevent identical duplicate comments on the same task by same user
        exists = Comment.objects.filter(task=task, user=request.user, comment=comment).exists()

        if exists:
            raise serializers.ValidationError({'comment': 'You have already posted an identical comment on this task.'})

        if task.project != project:
            raise serializers.ValidationError({"task": f"Task {task.id} is not associated with project {project.name}."})

        return attrs
        