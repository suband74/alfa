from django.contrib import admin
from .models import Player, Game


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ["name", "email", "date_create", "date_update"]
    list_editable = ["email"]
    search_fields = ["name", "email"]


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["name", "date_create", "date_update"]
    filter_horizontal = ["players"]
