from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register,      name="eraya-register"),
    path("login/",    views.login_verify,  name="eraya-login"),
]
