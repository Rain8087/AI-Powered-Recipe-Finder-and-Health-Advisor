# Generated by Django 5.0.3 on 2024-03-08 12:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('login', '0003_rename_id_myuser_userid_myuser_last_login_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='myuser',
            old_name='userid',
            new_name='id',
        ),
        migrations.RemoveField(
            model_name='myuser',
            name='last_login',
        ),
        migrations.AlterField(
            model_name='myuser',
            name='username',
            field=models.CharField(max_length=150, unique=True),
        ),
    ]
