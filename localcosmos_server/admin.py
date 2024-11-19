from django.contrib import admin

from .models import LocalcosmosUser


class UserAdmin(admin.ModelAdmin):
    exclude = ('last_login', 'password', 'date_joined')

admin.site.register(LocalcosmosUser, UserAdmin)
