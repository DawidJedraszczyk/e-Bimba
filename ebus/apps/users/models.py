from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.db import models
from django.conf import settings


class User(AbstractUser):
    slug = models.SlugField(unique=True, blank=True, db_index=True, max_length=200)
    pace = models.FloatField(verbose_name="Prędkość chodzenia [m/s]", default=settings.WALKING_SETTINGS['PACE'])
    max_distance = models.IntegerField(verbose_name="Maksymalna odległość pieszo [m]", default=settings.PROSPECTING_SETTINGS['START_RADIUS'])

    def __str__(self):
        return self.username

    def generate_unique_slug(self):
        base_slug = slugify(self.username)
        slug = base_slug
        counter = 1
        while User.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        super().save(*args, **kwargs)



