from django.urls import path
from . import views

app_name = 'tournament'

urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('confirmation/<uuid:token>/', views.confirmation, name='confirmation'),
    path('confirmation/<uuid:token>/invoice/', views.invoice_pdf, name='invoice_pdf'),
    path('donate-raffle-item/', views.raffle_donate, name='raffle_donate'),
    path('donate-raffle-item/thanks/', views.raffle_donate_thanks, name='raffle_donate_thanks'),
]
