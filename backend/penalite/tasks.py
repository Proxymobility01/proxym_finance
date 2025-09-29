# penalite/tasks.py
from celery import shared_task
from penalite.services import apply_penalties_for_now

@shared_task
def appliquer_penalite_12h():
    return apply_penalties_for_now(force_window="noon")

@shared_task
def appliquer_penalite_14h():
    return apply_penalties_for_now(force_window="fourteen")
