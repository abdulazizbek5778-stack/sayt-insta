from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('chat/', views.chat_page, name='chat'),
    path('chat/contacts/', views.chat_contacts, name='chat_contacts'),
    path('chat/users/<int:user_id>/messages/', views.chat_messages, name='chat_messages'),
    path('pricing/', views.pricing, name='pricing'),
    path('profile/', views.profile, name='profile'),
    path('u/<str:username>/', views.profile, name='user_profile'),
    path('u/<str:username>/<str:connection_type>/', views.user_connections, name='user_connections'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('stories/create/', views.create_story, name='create_story'),
    path('stories/<int:pk>/delete/', views.delete_story, name='delete_story'),
    path('stories/<int:story_id>/', views.story_viewer, name='story_viewer'),
    path('post/<int:pk>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:pk>/like/', views.toggle_like, name='toggle_like'),
    path('post/<int:pk>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:pk>/comments/', views.get_comments, name='get_comments'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete_comment'),
    path('follow/<str:username>/', views.toggle_follow, name='toggle_follow'),
    path('register/', views.register, name='register'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='app/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]