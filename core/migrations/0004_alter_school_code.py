from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_school_logo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="school",
            name="code",
            field=models.CharField(blank=True, editable=False, max_length=50, unique=True),
        ),
    ]
