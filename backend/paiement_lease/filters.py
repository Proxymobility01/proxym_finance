# filters.py
import django_filters as df
from .models import PaiementLease

class PaiementLeaseFilter(df.FilterSet):


    date_concernee = df.DateFilter(field_name="date_concernee")
    date_concernee_after  = df.DateFilter(field_name="date_concernee", lookup_expr="gte")
    date_concernee_before = df.DateFilter(field_name="date_concernee", lookup_expr="lte")

    created = df.DateFilter(method="filter_created_exact")
    created_after  = df.DateFilter(method="filter_created_after")
    created_before = df.DateFilter(method="filter_created_before")

    class Meta:
        model = PaiementLease
        fields = [
            "date_concernee", "date_concernee_after", "date_concernee_before",
            "created", "created_after", "created_before",
        ]

    def _day_bounds(self, value):
        """Calcule début et fin de journée locale et convertit en UTC pour comparer"""
        tz = timezone.get_current_timezone()  # Africa/Douala
        start_local = datetime.combine(value, time.min).replace(tzinfo=tz)
        end_local   = (datetime.combine(value, time.min) + timedelta(days=1)).replace(tzinfo=tz)
        # convertit en UTC (Python stdlib timezone.utc)
        return start_local.astimezone(py_timezone.utc), end_local.astimezone(py_timezone.utc)

    def filter_created_exact(self, qs, name, value):
        start, end = self._day_bounds(value)
        return qs.filter(created__gte=start, created__lt=end)

    def filter_created_after(self, qs, name, value):
        start, _ = self._day_bounds(value)
        return qs.filter(created__gte=start)

    def filter_created_before(self, qs, name, value):
        _, end = self._day_bounds(value)
        return qs.filter(created__lt=end)





import django_filters as df
from datetime import datetime, time, timedelta, timezone as py_timezone
from django.utils import timezone
from penalite.models import Penalite

class NonPaiementLeaseFilter(df.FilterSet):


    # date_concernee ( = date_paiement_manquee sur Penalite )
    date_concernee        = df.DateFilter(field_name="date_paiement_manquee")
    date_concernee_after  = df.DateFilter(field_name="date_paiement_manquee", lookup_expr="gte")
    date_concernee_before = df.DateFilter(field_name="date_paiement_manquee", lookup_expr="lte")


    class Meta:
        model = Penalite
        fields = [

            "date_concernee", "date_concernee_after", "date_concernee_before",
        ]


    # helpers pour bornes de journée locale -> UTC
    def _day_bounds(self, d):
        tz = timezone.get_current_timezone()
        start_local = datetime.combine(d, time.min).replace(tzinfo=tz)
        end_local   = (datetime.combine(d, time.min) + timedelta(days=1)).replace(tzinfo=tz)
        return start_local.astimezone(py_timezone.utc), end_local.astimezone(py_timezone.utc)

