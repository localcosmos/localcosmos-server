from django.contrib import admin

from .models import LocalcosmosUser


class UserAdmin(admin.ModelAdmin):
    pass

admin.site.register(LocalcosmosUser, UserAdmin)
