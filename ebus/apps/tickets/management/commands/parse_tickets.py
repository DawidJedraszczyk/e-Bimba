import json
from django.core.management.base import BaseCommand
from tickets.models import TicketType
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Load ticket types from tickets.json'

    def handle(self, *args, **kwargs):
        file_path = os.path.join(settings.STATIC_ROOT, 'tickets/tickets.json')

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        TicketType.objects.all().update(active=False)

        for city, categories in data.items():
            for category, tickets in categories.items():
                for name, details in tickets.items():
                    if details['Ulgowy']:

                        TicketType.objects.update_or_create(
                            name=name,
                            category=category,
                            discounted=True,
                            defaults={
                                'active': True,
                                'duration': details.get('Czas'),
                                'timestamp': details.get('Timestamp'),
                                'timestamp_type': details.get('TimestampType'),
                                'zone': details.get('Strefa'),
                                'price': details.get('Ulgowy'),
                                'currency': details.get('Waluta'),
                            }
                        )

                    if details['Normalny']:
                        TicketType.objects.update_or_create(
                            name=name,
                            category=category,
                            discounted=False,
                            defaults={
                                'active': True,
                                'duration': details.get('Czas'),
                                'timestamp': details.get('Timestamp'),
                                'timestamp_type': details.get('TimestampType'),
                                'zone': details.get('Strefa'),
                                'price': details.get('Ulgowy'),
                                'currency': details.get('Waluta'),
                            }
                        )
        self.stdout.write(self.style.SUCCESS('Ticket types loaded successfully!'))
