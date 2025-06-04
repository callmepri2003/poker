import random
from typing import List, Dict, Any
from .models import Game, Player, Card, Opponent


class GameService:
    """Service class for handling poker game logic"""
    
    SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    
    @classmethod
    def create_new_game(cls) -> Game:
        """Create a new poker game with initial setup"""
        game = Game.objects.create(
            phase='betting',
            pot=0,
            current_bet=10,
            can_call=True,
            can_raise=True,
            can_fold=True
        )
        
        # Create player
        player = Player.objects.create(game=game, chips=1000)
        
        # Create opponents
        opponent_names = ['Computer 1', 'Computer 2', 'Computer 3']
        for name in opponent_names:
            Opponent.objects.create(
                game=game,
                name=name,
                chips=random.randint(800, 1200),
                status='active',
                card_count=5
            )
        
        # Deal initial cards to player
        cls._deal_initial_cards(player)
        
        return game
    
    @classmethod
    def _deal_initial_cards(cls, player: Player):
        """Deal 5 random cards to the player"""
        # Create a deck
        deck = [(suit, rank) for suit in cls.SUITS for rank in cls.RANKS]
        random.shuffle(deck)
        
        # Deal 5 cards
        for i in range(5):
            suit, rank = deck[i]
            Card.objects.create(
                player=player,
                suit=suit,
                rank=rank,
                selected=False,
                position=i
            )
    
    @classmethod
    def process_bet_action(cls, game: Game, action: str, amount: int = None) -> Game:
        """Process a betting action"""
        if game.phase != 'betting':
            raise ValueError("Cannot bet when not in betting phase")
        
        player = game.player
        
        if action == 'fold':
            player.has_folded = True
            player.save()
            game.phase = 'finished'
            game.winner = random.choice(['Computer 1', 'Computer 2', 'Computer 3'])
            game.winning_hand = 'Pair of Kings'
            
        elif action == 'call':
            bet_amount = game.current_bet
            if player.chips < bet_amount:
                raise ValueError("Insufficient chips to call")
            
            player.chips -= bet_amount
            player.current_bet = bet_amount
            player.save()
            
            game.pot += bet_amount
            game.phase = 'drawing'
            
        elif action == 'raise':
            if not amount:
                raise ValueError("Amount required for raise")
            
            if amount < 0:
                raise ValueError("Raise amount must be positive")
            
            if player.chips < amount:
                raise ValueError("Insufficient chips to raise")
            
            player.chips -= amount
            player.current_bet = amount
            player.save()
            
            game.pot += amount
            game.current_bet = max(game.current_bet, amount)
            # Stay in betting phase for opponents to respond
        
        game.save()
        return game
    
    @classmethod
    def process_draw_action(cls, game: Game, discard_indices: List[int]) -> Game:
        """Process card drawing action"""
        if game.phase != 'drawing':
            raise ValueError("Cannot draw when not in drawing phase")
        
        player = game.player
        cards = list(player.cards.all().order_by('position'))
        
        # Validate indices
        for index in discard_indices:
            if index < 0 or index >= len(cards):
                raise ValueError(f"Invalid card index: {index}")
        
        # Remove discarded cards and deal new ones
        if discard_indices:
            # Create new deck (excluding current cards)
            current_cards = [(card.suit, card.rank) for card in cards]
            deck = [(suit, rank) for suit in cls.SUITS for rank in cls.RANKS 
                   if (suit, rank) not in current_cards]
            random.shuffle(deck)
            
            # Replace discarded cards
            for i, index in enumerate(sorted(discard_indices)):
                card = cards[index]
                suit, rank = deck[i]
                card.suit = suit
                card.rank = rank
                card.save()
        
        # Move to showdown/finished phase
        game.phase = 'finished'
        cls._determine_winner(game)
        game.save()
        
        return game
    
    @classmethod
    def _determine_winner(cls, game: Game):
        """Determine the winner of the game (simplified logic)"""
        # Simplified winner determination - randomly assign for testing
        possible_winners = ['player']
        for opponent in game.opponents.filter(status='active'):
            possible_winners.append(opponent.name)
        
        if not game.player.has_folded:
            game.winner = random.choice(possible_winners)
        else:
            # Player folded, opponent wins
            active_opponents = game.opponents.filter(status='active')
            if active_opponents:
                game.winner = random.choice(active_opponents).name
        
        # Set winning hand
        winning_hands = [
            'Royal Flush', 'Straight Flush', 'Four of a Kind',
            'Full House', 'Flush', 'Straight', 'Three of a Kind',
            'Two Pair', 'Pair of Aces', 'Pair of Kings', 'High Card'
        ]
        game.winning_hand = random.choice(winning_hands)
    
    @classmethod
    def get_game_state(cls, game_id: str) -> Game:
        """Get current game state"""
        try:
            return Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError("Game not found")