# Generated by Django 5.2 on 2025-04-09 13:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userProfile', '0002_task_user'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='tasks',
            field=models.ManyToManyField(to='userProfile.task'),
        ),
    ]
