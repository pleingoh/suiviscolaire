from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_schoolsetting"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="school",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="users",
                to="core.school",
            ),
        ),
    ]
