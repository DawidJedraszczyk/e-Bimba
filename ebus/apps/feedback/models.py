from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Feedback(models.Model):
    publication_datetime = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    rate = models.FloatField(default=0, verbose_name=_('Rating'))
    stored_data = models.JSONField(default=dict)

    url = models.CharField(max_length=200, default='')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)

