from django.contrib import admin

from django.contrib.auth.admin import UserAdmin
from .models import User, Follow


@admin.register(User)
class UserAdmin(UserAdmin):
    list_display = ('username',
                    'first_name',
                    'last_name', 'email',
                    'is_staff')
    list_filter = ('username', 'email')


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
