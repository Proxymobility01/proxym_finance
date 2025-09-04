# penalite/0002_penalite_contrat_chauffeur.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('penalite', '0001_initial'),
        ('contrat_chauffeur', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='penalite',
            name='contrat_chauffeur',
            field=models.ForeignKey(
                to='contrat_chauffeur.contratchauffeur',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='penalites',
                null=True, blank=True,  # garde temporairement nullable si des données existent
            ),
        ),
    ]
