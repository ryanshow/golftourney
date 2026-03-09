from django.urls import path
from . import views

app_name = 'tournament'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('confirmation/<int:pk>/', views.confirmation, name='confirmation'),
    path('donate-raffle-item/', views.raffle_donate, name='raffle_donate'),
    path('donate-raffle-item/thanks/', views.raffle_donate_thanks, name='raffle_donate_thanks'),
]
