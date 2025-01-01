from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
import uuid
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class TicketType(models.Model):
    active = models.BooleanField(default=True)
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    category = models.CharField(max_length=100)
    duration = models.CharField(max_length=50)
    timestamp = models.IntegerField()
    timestamp_type = models.CharField(max_length=20, choices=[('minutes', 'Minutes'), ('days', 'Days')])
    zone = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    discounted = models.BooleanField(default=False)
    currency = models.CharField(max_length=10)



    objects = models.Manager()
    active_tickets = ActiveManager()

    def __str__(self):
        discount_type = "Ulgowy" if self.discounted else "Normalny"
        return f"{self.name} - {discount_type}"

    def calculate_expiration(self):
        if self.timestamp_type == 'minutes':
            return now() + timedelta(minutes=self.timestamp)
        elif self.timestamp_type == 'days':
            return now() + timedelta(days=self.timestamp)
        return None


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT, related_name='tickets')
    ending_datetime = models.DateTimeField(null=True, blank=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    class Meta:
        ordering = ["-ending_datetime", "created_at"]

    def __str__(self):
        return f"Ticket {self.ticket_type.name} for {self.user.username}"

    def save(self, *args, **kwargs):
        if self.status == 'in_use' and not self.qr_code:
            qr_code_image = self.generate_qr_code_image()
            self.qr_code.save(f"{self.id}.png", qr_code_image, save=False)

        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.ending_datetime is None:
            return 'unused'
        elif now() > self.ending_datetime:
            return 'ended'
        else:
            return 'in_use'


    STATUS_CHOICES = (
        ('unused', 'Nie użyty'),
        ('in_use', 'Aktywny'),
        ('ended', 'Zakończony')
    )

    @property
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, 'Unknown')

    def generate_qr_code_image(self):
        qr = qrcode.make(self.id)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue())
