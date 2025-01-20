from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.timezone import now
from datetime import timedelta
import uuid
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class TicketType(models.Model):
    active = models.BooleanField(default=True, verbose_name=_("Active"))
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    city = models.CharField(max_length=50, verbose_name=_("City"))
    category = models.CharField(max_length=100, verbose_name=_("Category"))
    duration = models.CharField(max_length=50, verbose_name=_("Duration"))
    timestamp = models.IntegerField(verbose_name=_("Timestamp"))
    timestamp_type = models.CharField(
        max_length=20,
        choices=[
            ('minutes', _("Minutes")),
            ('days', _("Days"))
        ],
        verbose_name=_("Timestamp Type")
    )
    zone = models.CharField(max_length=100, verbose_name=_("Zone"))
    price = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_("Price"))
    discounted = models.BooleanField(default=False, verbose_name=_("Discounted"))
    currency = models.CharField(max_length=10, verbose_name=_("Currency"))

    objects = models.Manager()
    active_tickets = ActiveManager()

    class Meta:
        verbose_name = _("Ticket Type")
        verbose_name_plural = _("Ticket Types")

    def __str__(self):
        discount_type = _("Discounted") if self.discounted else _("Regular")
        return f"{self.name} - {discount_type}"

    def calculate_expiration(self):
        if self.timestamp_type == 'minutes':
            return now() + timedelta(minutes=self.timestamp)
        elif self.timestamp_type == 'days':
            return now() + timedelta(days=self.timestamp)
        return None


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name=_("ID"))
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name=_("User")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    ticket_type = models.ForeignKey(
        TicketType,
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name=_("Ticket Type")
    )
    ending_datetime = models.DateTimeField(null=True, blank=True, verbose_name=_("Ending Datetime"))
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name=_("QR Code"))

    class Meta:
        ordering = ["-ending_datetime", "created_at"]
        verbose_name = _("Ticket")
        verbose_name_plural = _("Tickets")

    def __str__(self):
        return _("Ticket {ticket_type} for {user}").format(ticket_type=self.ticket_type.name, user=self.user.username)

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
        ('unused', _("Unused")),
        ('in_use', _("In Use")),
        ('ended', _("Ended"))
    )

    @property
    def get_status_display(self):
        return dict(self.STATUS_CHOICES).get(self.status, _("Unknown"))

    def generate_qr_code_image(self):
        qr = qrcode.make(self.id)
        buffer = BytesIO()
        qr.save(buffer, format='PNG')
        return ContentFile(buffer.getvalue())
