from django.urls import path
from django.utils.translation import gettext_lazy as _
from .views import BuyTicketView, PaymentSuccessView, UseTicket, TicketDetail

app_name = 'tickets'

urlpatterns = [
    # URL for buying a ticket
    path(_('zakup-bilet/<str:ticket_type_id>/'), BuyTicketView.as_view(), name='buy_ticket'),

    # URL for payment success
    path(_('pomyślna-płatność/<int:ticket_type_id>/'), PaymentSuccessView.as_view(), name='payment_success'),

    # URL for using a ticket
    path(_('użyj-biletu/<uuid:id>/'), UseTicket.as_view(), name='use_ticket'),

    # URL for ticket details
    path(_('bilet/<uuid:pk>/'), TicketDetail.as_view(), name='ticket_detail'),
]
