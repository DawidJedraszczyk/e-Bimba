from django.views.generic import View, DetailView
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from .models import TicketType, Ticket


class BuyTicketView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        ticket_type = get_object_or_404(TicketType, id=kwargs['ticket_type_id'])

        payment_data = {
            'ticket_id': ticket_type.id,
            'user_id': request.user.id,
            'price': ticket_type.price,
            'currency': ticket_type.currency,
            'callback_url': request.build_absolute_uri(
                reverse('tickets:payment_success', kwargs={'ticket_type_id': ticket_type.id})
            ),
        }
        return render(request, 'tickets/payment_page.html', {'payment_data': payment_data})


class PaymentSuccessView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        ticket_type = get_object_or_404(TicketType, id=kwargs['ticket_type_id'])

        Ticket.objects.create(
            user=request.user,
            ticket_type=ticket_type,
            status='unused',
            ending_datetime=ticket_type.calculate_expiration(),
        )

        messages.success(request, f"Pomyślnie zakupiono bilet: {ticket_type.name}")

        return redirect('users:user_detail')


class UseTicket(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        ticket = get_object_or_404(Ticket, id=kwargs['id'])

        ticket.ending_datetime = ticket.ticket_type.calculate_expiration()
        ticket.save()

        messages.success(request, f"Pomyślnie wygenerowano kod QR. Bilet zakończy się: {ticket.ending_datetime}")

        return redirect('tickets:ticket_detail', pk=ticket.id)


class TicketDetail(LoginRequiredMixin, DetailView):
    model = Ticket

