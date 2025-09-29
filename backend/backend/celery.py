# backend/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# définit le module de configuration Celery à utiliser
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')

# Utilise les paramètres définis dans settings.py pour configurer Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découvre automatiquement les tâches Celery dans les apps Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
