# Generated by Django 5.1.3 on 2024-12-13 16:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authenticate', '0012_notification'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Notification',
        ),
    ]