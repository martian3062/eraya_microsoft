from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    email    = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")
    name     = request.data.get("name", "").strip() or email.split("@")[0]

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)
    if len(password) < 6:
        return Response({"error": "Password must be at least 6 characters"}, status=400)
    if User.objects.filter(username=email).exists():
        return Response({"error": "An account with this email already exists"}, status=409)

    user = User.objects.create_user(
        username=email, email=email, password=password, first_name=name
    )
    return Response({
        "id": str(user.id), "email": user.email,
        "name": user.first_name or user.username,
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def login_verify(request):
    email    = request.data.get("email", "").strip().lower()
    password = request.data.get("password", "")

    user = authenticate(username=email, password=password)
    if user is None:
        return Response({"error": "Invalid email or password"}, status=401)

    return Response({
        "id": str(user.id), "email": user.email,
        "name": user.first_name or user.username or email,
    })
