
from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('payments/<str:order_number>', views.payments, name='payments'),
    path('payments-success/',
         views.payments_success, name='payments_success'),
    path('payments-failed/', views.payments_failed, name='payments_failed'),
    path('charge/', views.charge, name='charge')

]
