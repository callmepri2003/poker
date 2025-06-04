from django.contrib import admin
from .models import Game, Player, Card, Opponent


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ['id', 'phase', 'pot', 'current_bet', 'winner', 'created_at']
    list_filter = ['phase', 'created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    search_fields = ['id', 'winner']


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ['game', 'chips', 'has_folded', 'current_bet']
    list_filter = ['has_folded']
    search_fields = ['game__id']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['player', 'suit', 'rank', 'position', 'selected']
    list_filter = ['suit', 'rank', 'selected']
    search_fields = ['player__game__id']
    ordering = ['player', 'position']


@admin.register(Opponent)
class OpponentAdmin(admin.ModelAdmin):
    list_display = ['game', 'name', 'status', 'chips', 'card_count']
    list_filter = ['status']
    search_fields = ['game__id', 'name']