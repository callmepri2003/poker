import uuid
import json
from decimal import Decimal
from django.db import models
from django.contrib.postgres.fields import JSONField


class Game(models.Model):
    PHASE_CHOICES = [
        ('betting', 'Betting'),
        ('drawing', 'Drawing'),
        ('showdown', 'Showdown'),
        ('finished', 'Finished'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES, default='betting')
    pot = models.IntegerField(default=0)
    current_bet = models.IntegerField(default=10)
    winner = models.CharField(max_length=50, null=True, blank=True)
    winning_hand = models.CharField(max_length=100, null=True, blank=True)
    can_call = models.BooleanField(default=True)
    can_raise = models.BooleanField(default=True)
    can_fold = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Game {self.id} - {self.phase}"


class Player(models.Model):
    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name='player')
    chips = models.IntegerField(default=1000)
    has_folded = models.BooleanField(default=False)
    current_bet = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Player in game {self.game.id}"


class Card(models.Model):
    SUIT_CHOICES = [
        ('hearts', 'Hearts'),
        ('diamonds', 'Diamonds'),
        ('clubs', 'Clubs'),
        ('spades', 'Spades'),
    ]
    
    RANK_CHOICES = [
        ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), ('6', '6'),
        ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'),
        ('J', 'Jack'), ('Q', 'Queen'), ('K', 'King'), ('A', 'Ace'),
    ]
    
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='cards')
    suit = models.CharField(max_length=10, choices=SUIT_CHOICES)
    rank = models.CharField(max_length=3, choices=RANK_CHOICES)
    selected = models.BooleanField(default=False)
    position = models.IntegerField(default=0)  # Position in hand (0-4)
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.rank} of {self.suit}"


class Opponent(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('folded', 'Folded'),
        ('all_in', 'All In'),
    ]
    
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='opponents')
    name = models.CharField(max_length=50)
    chips = models.IntegerField(default=1000)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    card_count = models.IntegerField(default=5)
    current_bet = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.name} in game {self.game.id}"