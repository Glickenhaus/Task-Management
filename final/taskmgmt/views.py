from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer, ProjectSerializer, RoleSerializer, TaskSerializer, CommentSerializer
from .models import Project, Task, Comment, Member
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import status, serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .permissions import IsOwnerOrAdmin, IsMember, IsOwner, CanManageTask
from rest_framework.permissions import IsAuthenticated, IsAdminUser

User = get_user_model()

# Create your views here.
@extend_schema(
    operation_id="register",
    summary="Register",
    description="Takes user credentials (username, email and password), and stores them in db.",
    request=RegisterSerializer,
    responses={
        201: OpenApiResponse(description="User Created."),
        400: OpenApiResponse(description="Check inputed credenntials for username, email or password.")
    },
    tags=["Register"]
)
# Create your views here.
class Register(APIView):
    permission_classes = []

    # Enter credentials to register
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({"Status": "User Created",
                        "User": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                        }
                        },
                        status=status.HTTP_201_CREATED)
    
@extend_schema(
    operation_id="login",
    summary="Login",
    description="Verifies the credentials passed match, and issues JWT Tokens to the user.",
    request=LoginSerializer,
    responses={
        200: OpenApiResponse(description="Login Successful."),
        401: OpenApiResponse(description="No matching credentials found.")
    },
    tags=["Login"]
)
    
class Login(TokenObtainPairView):

    permission_classes = []
    serializer_class = LoginSerializer

class Users(APIView):
    @extend_schema(
        operation_id="view_my_profile",
        summary="View Profile",
        description="Displays the information of the user. Auth is required.",
        request=RegisterSerializer,
        responses={
            200: OpenApiResponse(description="Displays user info."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
        },
        tags=["Users"]
    )

    # Get my profile
    def get(self, request):
        serializer = RegisterSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="change_my_password",
        summary="Change Password",
        description="Allows the user to change their password. Auth is required.",
        request=ChangePasswordSerializer,
        responses={
            200: OpenApiResponse(description="Displays user info."),
            400: OpenApiResponse(description="Old and new password must not be same; or password criteria not met"),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
        },
        tags=["Users"]
    )
    # Change my password
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        outstanding_tokens = OutstandingToken.objects.filter(user=user)
        for token in outstanding_tokens:
            BlacklistedToken.objects.get_or_create(token=token)
             
        return Response({'Status': 'Password Updated Successfully'}, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_my_user",
        summary="Delete Account",
        description="Allows the user to delete their account. Auth is required.",
        responses={
            205: OpenApiResponse(description="Deletion Successful."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            404: OpenApiResponse(description="User not found.")
        },
        tags=["Users"]
    )
    # Delete my account
    def delete(self, request):
        user = get_object_or_404(User, username=self.request.user)
        user.delete()

        return Response({'Status': 'Deleted Account Successfully.'}, status=status.HTTP_205_RESET_CONTENT)

        
@extend_schema(
    operation_id="logout",
    summary="Logout",
    description="Logs out the user after their refesh token is passed. Auth is required.",
    request=inline_serializer(name="LogoutRequest", fields={'refresh': serializers.CharField(help_text='The refresh token to blacklist after logout.')}),
    responses={
        205: OpenApiResponse(description="Logout Successful."),
        400: OpenApiResponse(description="Refresh Token is either expired, invalid or blacklisted."),
        401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
    },
    tags=["Logout"]
)
class Logout(APIView):

    # Pass refresh token so as to blacklist
    def post(self, request):
        refresh_token = request.data.get('refresh')
        try:
            # 2. Instantiate and blacklist the token
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"Status": "Logged out successfully."}, status=status.HTTP_205_RESET_CONTENT)

        except TokenError as e:
            # 3. Catch invalid, expired, or already blacklisted tokens
            return Response({"Error": "Token is invalid, expired, or already blacklisted."}, status=status.HTTP_400_BAD_REQUEST)

class ProjectView(APIView):

    def get_permissions(self):
        permission_classes = [IsAuthenticated]

        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes.append(IsOwner)

        return [permission() for permission in permission_classes]

    @extend_schema(
        operation_id="get_member_projects",
        summary="View Projects",
        description="Enables an authenticated user to view all projects they belong to.",
        request=ProjectSerializer,
        responses={
            200: OpenApiResponse(description="Shows all projects the user belongs to."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
        },
        tags=["Project"]
    )
    # View Created Projects
    def get(self, request):
        data = Project.objects.filter(members=self.request.user)
        if request.user.is_superuser:
            data = Project.objects.all()
        serializer = ProjectSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="create_a_project",
        summary="Create Project",
        description="Enables an authenticated user to create a project.",
        request=ProjectSerializer,
        responses={
            201: OpenApiResponse(description="Project Created."),
            400: OpenApiResponse(description="Check credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
        },
        tags=["Project"]
    )
    # Create Project
    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(owner=self.request.user)

        Member.objects.create(project=project, user=self.request.user, role=Member.Role.OWNER)

        members = self.request.data.get('members', [])
        if members:
            # Fetch matching users in a single query, excluding the creator
            members_to_add = User.objects.filter(username__in=members).exclude(id=self.request.user.id)
            members_to_create = [
                Member.objects.create(project=project, user=user, role=Member.Role.MEMBER)
                for user in members_to_add
            ]
        if members_to_create:
            Member.objects.bulk_create(members_to_create, ignore_conflicts=True)

        # Re-serialize so 'members' includes the creator + added users
        response_serializer = ProjectSerializer(project)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="update_project",
        summary="Update Project Info",
        description="Enables an authenticated user to modify a project created by them.",
        request=ProjectSerializer,
        responses={
            200: OpenApiResponse(description="Project Modified."),
            400: OpenApiResponse(description="Check credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Project"]
    )
    # Modify Project
    def patch(self, request, pk):
        data = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, data)
        serializer = ProjectSerializer(data, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_project",
        summary="Delete Project",
        description="Enables an authenticated user to delete a project created by them.",
        responses={
            205: OpenApiResponse(description="Project Deleted."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Project"]
    )
    # Delete Project
    def delete(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        project.delete()

        return Response({"Message": "Project Deleted Successfully."}, status=status.HTTP_205_RESET_CONTENT)

class RoleChange(APIView):
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(
        operation_id="change_role",
        summary="Change Role",
        description="Enables an authenticated user to change the role of a user in a project. Restricted to project owner or admins.",
        request=RoleSerializer,
        responses={
            200: OpenApiResponse(description="Role Changed."),
            400: OpenApiResponse(description="Check credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Project"]
    )
    # Change Project Member Role
    def put(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)

        username = request.data.get('username')

        member = get_object_or_404(Member, project=project, user__username=username)
        serializer = RoleSerializer(member, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

class AddMember(APIView):
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(
        operation_id="view_project_members",
        summary="View Project Members",
        description="Enables an authenticated user to view members associated with a specific project. Restricted to the project owner or admins.",
        request=ProjectSerializer,
        responses={
            200: OpenApiResponse(description="Views Project Members."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found")
        },
        tags=["Project"]
    )
    # View Project Members
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        members = Member.objects.filter(project=project)
        serializer = RoleSerializer(members, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="add_project_members",
        summary="Add Members",
        description="Enables an authenticated user to add members to a specific project. Restricted to the project owner or admins.",
        request=inline_serializer(name="AddMembers", fields={'members': serializers.ListField(help_text="A list of members to be added.")}),
        responses={
            200: OpenApiResponse(description="Adds Members."),
            400: OpenApiResponse(description="Check Credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Project"]
    )
    # Add Members to Project
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)

        usernames = request.data.get('members', [])
        invalid = []

        # # 1. Fetch all existing User objects that match any of the provided usernames in ONE database query
        # existing_users = User.objects.filter(username__in=usernames)

        # # 2. Create a set of found usernames for fast lookup
        # existing_usernames = set(existing_users.values_list('username', flat=True))

        # # 3. Find which requested usernames do not exist in the database
        # invalid_users = [u for u in usernames if u not in existing_usernames]

        # # 4. If there are invalid usernames, return error response containing ALL of them
        # if invalid_users:
        # return Response(
        #     {"error": f"The following usernames are invalid: {', '.join(invalid_users)}"}, 
        #     status=status.HTTP_400_BAD_REQUEST
        # )

        if not isinstance(usernames, list) or not usernames:
            return Response({"Requirement": "A non-empty username list."}, status=status.HTTP_400_BAD_REQUEST)
        for user in usernames:
            if not User.objects.filter(username=user).exists():
                invalid.append(user)
        if invalid:
            return Response({f"{invalid} invalid."}, status=status.HTTP_400_BAD_REQUEST)

        users_to_add = User.objects.filter(username__in=usernames).exclude(username__in=project.members.values_list('username'))

        new_members = [
            Member.objects.create(project=project, user=user, role=Member.Role.MEMBER)
            for user in users_to_add
        ]
        Member.objects.bulk_create(new_members, ignore_conflicts=True)

        response_serializer = ProjectSerializer(project)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

class RemoveMember(APIView):
    permission_classes = [IsOwnerOrAdmin]

    @extend_schema(
        operation_id="remove_project_members",
        summary="Remove Members",
        description="Enables an authenticated user to remove members from a specific project. Restricted to the project owner or admins.",
        request=inline_serializer(name="RemoveMembers", fields={'members': serializers.ListField(help_text="A list of members to be removed.")}),
        responses={
            200: OpenApiResponse(description="Removes Members."),
            400: OpenApiResponse(description="Check Credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Project"]
    )
    # Remove Project Member
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)

        usernames = request.data.get('members', [])
        not_part = []
        invalid = []
        if not isinstance(usernames, list) or not usernames:
            return Response({"Requirement": "A non-empty username list."}, status=status.HTTP_400_BAD_REQUEST)
        for user in usernames:
            if not Member.objects.filter(project=project, user__username__in=usernames).exists():
                not_part.append(user)
            if not User.objects.filter(username=user).exists():
                invalid.append(user)
        if invalid:
            return Response({f"{invalid} invalid."}, status=status.HTTP_400_BAD_REQUEST)
        if not_part:
            return Response({f"{not_part} not associated with this project."}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = Member.objects.filter(project=project, user__username__in=usernames).exclude(role=Member.Role.OWNER).delete()

        response_serializer = ProjectSerializer(project)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

class Tasks(APIView):

    permission_classes = [CanManageTask]

    @extend_schema(
    operation_id="get_project_tasks",
    summary="View Project Tasks",
    description="Enables an authenticated user to view the tasks associated with a project. Restricted to project members.",
    request=TaskSerializer,
    responses={
        200: OpenApiResponse(description="Displays Project Tasks."),
        401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
        403: OpenApiResponse(description="Not authorized to perform action."),
        404: OpenApiResponse(description="Project not found.")
    },
    tags=["Task"]
    )
    # Get Project Tasks
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        data = Task.objects.filter(project=project)
        serializer = TaskSerializer(data, many=True)

        return Response(serializer.data)

    @extend_schema(
        operation_id="create_task",
        summary="Create Task",
        description="Enables an authenticated user to create a task in a specific project they belong to.",
        request=TaskSerializer,
        responses={
            200: OpenApiResponse(description="Removes Members."),
            400: OpenApiResponse(description="Check Credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found.")
        },
        tags=["Task"]
    )
    # Create a Task
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        serializer = TaskSerializer(data=request.data, context={'request': request, 'project': project})
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project, created_by=self.request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="update_task",
        summary="Update Task",
        description="Enables an authenticated user to update a task's standing. Members can only update status, the rest are handled by owners or admins.",
        request=TaskSerializer,
        responses={
            200: OpenApiResponse(description="Task Updated."),
            400: OpenApiResponse(description="Check credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized."),
            404: OpenApiResponse(description="Project or task not found.")
        },
        tags=["Task"]
    )
    # Update Task
    def patch(self, request, pk, pkt):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        task = get_object_or_404(Task, pk=pkt)
        serializer = TaskSerializer(task, data=request.data, partial=True, context={'request': request, 'project': project, 'task': task})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="delete_task",
        summary="Delete Task",
        description="Enables an authenticated user to delete a task in a project where they belong to. Restricted to project owners or admins.",
        responses={
            205: OpenApiResponse(description="Task Deleted."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project or task not found.")
        },
        tags=["Task"]
    )
    def delete(self, request, pk, pkt):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        task = get_object_or_404(Task, pk=pkt)

        if task.project != project:
            return Response({"task": "You can not delete a task of a project it does not belong to."}, status=status.HTTP_403_FORBIDDEN)

        task.delete()
        return Response({f"Task ({task.title}) deleted successfully."}, status=status.HTTP_205_RESET_CONTENT)

class Comments(APIView):

    permission_classes = [IsMember]

    @extend_schema(
    operation_id="get_project_comments",
    summary="View Project Comments",
    description="Enables an authenticated user to view the comments associated with a project. Restricted to project members.",
    request=CommentSerializer,
    responses={
        200: OpenApiResponse(description="Displays Project Comments."),
        401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
        403: OpenApiResponse(description="Not authorized to perform action."),
        404: OpenApiResponse(description="Project not found.")
    },
    tags=["Task"]
    )
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        comment = Comment.objects.filter(task__project=project)
        serializer = CommentSerializer(comment, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="make_comment",
        summary="Comment on a task",
        description="Enables an authenticated user to comment on a task in a specific project they belong to.",
        request=CommentSerializer,
        responses={
            201: OpenApiResponse(description="Comment Made."),
            400: OpenApiResponse(description="Check Credentials."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project or task not found.")
        },
        tags=["Task"]
    )
    def post(self, request, pk, pkt):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        task = get_object_or_404(Task, pk=pkt)
        serializer = CommentSerializer(data=request.data, context={'request': request, 'project': project, 'task': task})
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task, user=self.request.user)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class Admin(APIView):
    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="get_all_users",
        summary="All Users",
        description="Fetches the information of all registered users. Admin Auth is required.",
        request=RegisterSerializer,
        responses={
            200: OpenApiResponse(description="Displays all users'information."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform this action.")
        },
        tags=["Admin"]
    )
    # Get all users
    def get(self, request):
        all_users = User.objects.all()
        serializer = RegisterSerializer(all_users, many=True)
        return Response(serializer.data)

    @extend_schema(
        operation_id="delete_user",
        summary="Delete User",
        description="Deletes a user's account relative to their id. Admin Auth is required.",
        responses={
            205: OpenApiResponse(description="Deletion Successful."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform this action."),
            404: OpenApiResponse(description="User not found.")
        },
        tags=["Admin"]
    )
    # Delete user
    def delete(self, request, id):
        user = get_object_or_404(User, id=id)
        if user == self.request.user:
            return Response("You cannot delete your account.", status=status.HTTP_406_NOT_ACCEPTABLE)
        user.delete()
        return Response({'Status': f"Deleted user {user.username.title()}."}, status=status.HTTP_205_NO_CONTENT)


class AdminProject(APIView):

    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="get_all_info",
        summary="Get All Information",
        description="Fetches the information of all projects, tasks, and comments. Admin Auth is required.",
        request=(ProjectSerializer, TaskSerializer, CommentSerializer),
        responses={
            200: OpenApiResponse(description="Displays all information."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform this action.")
        },
        tags=["Admin"]
    )
    def get(self, request):
        project = Project.objects.all()
        task = Task.objects.all()
        comment = Comment.objects.all()
        serializer = ProjectSerializer(project, many=True)
        serial = TaskSerializer(task, many=True)
        ser = CommentSerializer(comment, many=True)

        return Response(({"Projects": serializer.data}, {"Tasks": serial.data}, {"Comments": ser.data}), status=status.HTTP_200_OK)

        
