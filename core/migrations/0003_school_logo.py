from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_schoolsetting"),
    ]

    operations = [
        migrations.AddField(
            model_name="school",
            name="logo",
            field=models.ImageField(blank=True, null=True, upload_to="schools/logos/"),
        ),
    ]
