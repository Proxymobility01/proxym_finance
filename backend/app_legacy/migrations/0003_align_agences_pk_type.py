from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app_legacy', '0002_alter_agences_options_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='agences',
                    name='id',
                    field=models.PositiveBigIntegerField(primary_key=True, serialize=False),
                ),
            ],
        ),
    ]
