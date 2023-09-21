from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.db.models import CheckConstraint, F, Q


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator
    username = models.CharField(
        max_length=settings.MAX_USERNAME_LENGTH,
        unique=True,
        validators=[username_validator],)
    password = models.CharField(
        max_length=settings.MAX_PASSWORD_LENGTH)
    email = models.EmailField(
        max_length=settings.MAX_EMAIL_LENGTH, unique=True)
    first_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH)
    last_name = models.CharField(
        max_length=settings.MAX_NAME_LENGTH)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('username',)


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='Вы подписаны на данного автора',
            ),
            CheckConstraint(
                name='user_not_equal_author',
                check=~Q(user=F('author')),
            ),
        ]
