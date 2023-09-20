# Generated by Django 3.2 on 2023-09-20 06:42

import django.contrib.auth.validators
from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_alter_user_username'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'ordering': ('username',)},
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()]),
        ),
        migrations.AddConstraint(
            model_name='follow',
            constraint=models.CheckConstraint(check=models.Q(_negated=True, user=django.db.models.expressions.F('author')), name='user_not_equal_author'),
        ),
    ]
