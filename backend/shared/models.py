from django.db import models

class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # fills on insert
    updated = models.DateTimeField(auto_now=True)      # updates on save

    class Meta:
        abstract = True


