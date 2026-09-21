from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer, ProjectSerializer, TaskSerializer, CommentSerializer
from .models import Project, Task, Comment, Member
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import status, serializers
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from .permissions import IsOwnerOrAdmin, IsMember, IsOwner
from rest_framework.permissions import IsAdminUser, IsAuthenticated

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
    request=ChangePasswordSerializer,
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
            204: OpenApiResponse(description="Deletion Successful."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            404: OpenApiResponse(description="User not found.")
        },
        tags=["Users"]
    )
    # Delete my account
    def delete(self, request):
        user = get_object_or_404(User, username=self.request.user)
        user.delete()

        return Response({'Status': 'Deleted Account Successfully.'}, status=status.HTTP_204_NO_CONTENT)

        
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
        operation_id="get_created_projects",
        summary="View Projects",
        description="Enables an authenticated user to view all projects created by them.",
        request=ProjectSerializer,
        responses={
            200: OpenApiResponse(description="Shows all projects created by the user."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token.")
        },
        tags=["Project"]
    )
    def get(self, request):
        data = Project.objects.filter(members=self.request.user)
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
        request=ProjectSerializer,
        responses={
            205: OpenApiResponse(description="Project Created."),
            401: OpenApiResponse(description="Unauthenticated or Invalid Token."),
            403: OpenApiResponse(description="Not authorized to perform action."),
            404: OpenApiResponse(description="Project not found")
        },
        tags=["Project"]
    )
    def delete(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        self.check_object_permissions(request, project)
        project.delete()

        return Response({"Message": "Project Deleted Successfully."}, status=status.HTTP_205_RESET_CONTENT)

        
