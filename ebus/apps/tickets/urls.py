from django.urls import path
from .views import BuyTicketView, PaymentSuccessView, UseTicket, TicketDetail

app_name = 'tickets'

urlpatterns = [
    path('zakup-bilet/<str:ticket_type_id>/', BuyTicketView.as_view(), name='buy_ticket'),
    path('pomyślna-płatność/<int:ticket_type_id>/', PaymentSuccessView.as_view(), name='payment_success'),
    path('użyj-biletu/<uuid:id>', UseTicket.as_view(), name='use_ticket'),
    path('bilet/<uuid:pk>/', TicketDetail.as_view(), name='ticket_detail'),
]
