from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.conf import settings


class User(AbstractUser):

    username = models.CharField(
        max_length=settings.MAX_USERNAME_LENGTH,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message='''Имя пользователя может
                содержать только буквы,
                цифры и символы @/./+/-/_''',
                code='invalid_username',
            ),
        ],
    )
    password = models.CharField(
        max_length=settings.MAX_PASSWORD_LENGTH)
    email = models.EmailField(
        max_length=settings.MAX_EMAIL_LENGTH, unique=True)
    first_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH)
    last_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        ordering = ['username']


class Follow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='Вы подписаны на данного автора',
            ),
        ]
