from django.urls import path
from . import views


urlpatterns = [
    path('hello/', views.hello, name='hello'),
    path('', views.get_users, name='get_users'),
    path('create/', views.create_user, name='create_user'),
    path('login/', views.login, name='login_user'),
    path("me/", views.get_current_user, name="get_current_user"),
    path("verify/<str:token>/", views.user_verification, name="user_verification"),
    path("verify-token/", views.verify_token_session, name="verify_token"),
]
