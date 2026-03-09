from django.urls import path
from . import views

app_name = 'tournament'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('confirmation/<int:pk>/', views.confirmation, name='confirmation'),
]
