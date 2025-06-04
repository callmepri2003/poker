from rest_framework import serializers
from .models import Game, Player, Card, Opponent


class CardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Card
        fields = ['suit', 'rank', 'selected']


class OpponentSerializer(serializers.ModelSerializer):
    cardCount = serializers.IntegerField(source='card_count')
    
    class Meta:
        model = Opponent
        fields = ['id', 'name', 'status', 'chips', 'cardCount']


class GameStateSerializer(serializers.ModelSerializer):
    gameId = serializers.CharField(source='id')
    playerHand = serializers.SerializerMethodField()
    playerChips = serializers.SerializerMethodField()
    opponents = OpponentSerializer(many=True, read_only=True)
    canCall = serializers.BooleanField(source='can_call')
    canRaise = serializers.BooleanField(source='can_raise')
    canFold = serializers.BooleanField(source='can_fold')
    currentBet = serializers.IntegerField(source='current_bet')
    winningHand = serializers.CharField(source='winning_hand')
    
    class Meta:
        model = Game
        fields = [
            'gameId', 'phase', 'pot', 'playerHand', 'playerChips',
            'opponents', 'winner', 'winningHand', 'canCall',
            'canRaise', 'canFold', 'currentBet'
        ]
    
    def get_playerHand(self, obj):
        try:
            player = obj.player
            cards = player.cards.all().order_by('position')
            return CardSerializer(cards, many=True).data
        except Player.DoesNotExist:
            return []
    
    def get_playerChips(self, obj):
        try:
            return obj.player.chips
        except Player.DoesNotExist:
            return 1000


class BetActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['call', 'raise', 'fold'])
    amount = serializers.IntegerField(required=False, min_value=1)
    
    def validate(self, data):
        if data['action'] == 'raise' and 'amount' not in data:
            raise serializers.ValidationError("Amount is required for raise action")
        return data


class DrawActionSerializer(serializers.Serializer):
    discardIndices = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=4),
        allow_empty=True,
        max_length=5
    )
    
    def validate_discardIndices(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate indices are not allowed")
        return value