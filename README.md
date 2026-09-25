# Task-Management-API

This collection provides a full set of endpoints for testing a task management API with role-based access control.
It is organized into four sections:
Auth – user registration, login, and logout
Admin – administrative operations including listing all users, viewing all projects/tasks/comments, and deleting users
User – user profile management, including viewing profile, changing password, and deleting account
Project – full project lifecycle management, including creating, updating, and deleting projects, managing project members and roles, and nested task operations (create, update, delete, comment, and view comments)

Bearer token authorization via {{access_token}} is applied at the collection level and inherited across all requests.
