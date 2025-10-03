from django.db import models

class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)  # fills on insert
    updated = models.DateTimeField(auto_now=True)      # updates on save

    class Meta:
        abstract = True



from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000