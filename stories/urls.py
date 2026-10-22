from django.urls import path

from . import views

app_name = 'stories'

urlpatterns = [
	path('', views.index, name='index'),
	path('archive/', views.archive, name='archive'),
	path('create/', views.create, name='create'),
]
