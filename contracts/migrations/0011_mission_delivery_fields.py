from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contracts', '0010_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='mission',
            name='delivery_note',
            field=models.TextField(blank=True, verbose_name='Note de livraison'),
        ),
        migrations.AddField(
            model_name='mission',
            name='completed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
