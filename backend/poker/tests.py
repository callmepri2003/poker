import json
import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Game, Player, Card, Opponent
from .serializers import GameStateSerializer
from .views import GameViewSet


class PokerGameAPITestCase(APITestCase):
    """Base test case with common setup for poker game tests"""
    
    def setUp(self):
        self.client = APIClient()
        self.game_data = {
            'gameId': str(uuid.uuid4()),
            'phase': 'betting',
            'pot': 0,
            'playerHand': [],
            'playerChips': 1000,
            'opponents': [],
            'winner': None,
            'winningHand': None,
            'canCall': True,
            'canRaise': True,
            'canFold': True,
            'currentBet': 10
        }
    
    def create_sample_game(self):
        """Helper method to create a sample game for testing"""
        response = self.client.post('/api/v1/game/')
        return response.data['gameId']
    
    def create_sample_cards(self):
        """Helper method to create sample cards"""
        return [
            {'suit': 'hearts', 'rank': 'A', 'selected': False},
            {'suit': 'spades', 'rank': 'K', 'selected': False},
            {'suit': 'diamonds', 'rank': 'Q', 'selected': False},
            {'suit': 'clubs', 'rank': 'J', 'selected': False},
            {'suit': 'hearts', 'rank': '10', 'selected': False}
        ]


class GameCreationTestCase(PokerGameAPITestCase):
    """Test cases for game creation endpoint"""
    
    def test_create_new_game_success(self):
        """Test successful game creation"""
        url = '/api/v1/game/'
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('gameId', response.data)
        self.assertEqual(response.data['phase'], 'betting')
        self.assertEqual(response.data['pot'], 0)
        self.assertEqual(len(response.data['playerHand']), 5)  # Should deal 5 cards
        self.assertEqual(response.data['playerChips'], 1000)  # Default starting chips
        self.assertEqual(len(response.data['opponents']), 3)  # 3 computer opponents
        self.assertTrue(response.data['canCall'])
        self.assertTrue(response.data['canRaise'])
        self.assertTrue(response.data['canFold'])
        self.assertIsNone(response.data['winner'])
    
    def test_create_game_validates_card_structure(self):
        """Test that created game has properly structured cards"""
        response = self.client.post('/api/v1/game/')
        
        for card in response.data['playerHand']:
            self.assertIn('suit', card)
            self.assertIn('rank', card)
            self.assertIn('selected', card)
            self.assertIn(card['suit'], ['hearts', 'diamonds', 'clubs', 'spades'])
            self.assertIn(card['rank'], ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'])
            self.assertFalse(card['selected'])  # Cards should not be selected initially
    
    def test_create_game_validates_opponents_structure(self):
        """Test that created game has properly structured opponents"""
        response = self.client.post('/api/v1/game/')
        
        for opponent in response.data['opponents']:
            self.assertIn('id', opponent)
            self.assertIn('name', opponent)
            self.assertIn('status', opponent)
            self.assertIn('chips', opponent)
            self.assertIn('cardCount', opponent)
            self.assertEqual(opponent['status'], 'active')
            self.assertEqual(opponent['cardCount'], 5)
            self.assertGreater(opponent['chips'], 0)
    
    @patch('poker.views.GameService.create_new_game')
    def test_create_game_server_error(self, mock_create_game):
        """Test server error during game creation"""
        mock_create_game.side_effect = Exception("Database error")
        
        response = self.client.post('/api/v1/game/')
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class GameStateRetrievalTestCase(PokerGameAPITestCase):
    """Test cases for game state retrieval endpoint"""
    
    def test_get_game_state_success(self):
        """Test successful game state retrieval"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['gameId'], game_id)
        self.assertIn('phase', response.data)
        self.assertIn('pot', response.data)
        self.assertIn('playerHand', response.data)
        self.assertIn('opponents', response.data)
    
    def test_get_game_state_not_found(self):
        """Test game state retrieval for non-existent game"""
        fake_game_id = str(uuid.uuid4())
        url = f'/api/v1/game/{fake_game_id}/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_get_game_state_invalid_uuid(self):
        """Test game state retrieval with invalid UUID"""
        url = '/api/v1/game/invalid-uuid/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BettingActionTestCase(PokerGameAPITestCase):
    """Test cases for betting actions"""
    
    def test_call_action_success(self):
        """Test successful call action"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'call'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('gameId', response.data)
        self.assertGreaterEqual(response.data['pot'], 10)  # Pot should increase
    
    def test_fold_action_success(self):
        """Test successful fold action"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'fold'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phase'], 'finished')
        self.assertIsNotNone(response.data['winner'])
    
    def test_raise_action_success(self):
        """Test successful raise action"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'raise', 'amount': 50}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['pot'], 50)
        self.assertGreaterEqual(response.data['currentBet'], 50)
    
    def test_raise_action_missing_amount(self):
        """Test raise action without amount"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'raise'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_raise_action_invalid_amount(self):
        """Test raise action with invalid amount"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'raise', 'amount': -10}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_raise_action_insufficient_chips(self):
        """Test raise action with insufficient chips"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'raise', 'amount': 2000}  # More than starting chips
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_invalid_bet_action(self):
        """Test invalid bet action"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'invalid_action'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bet_action_game_not_found(self):
        """Test betting action on non-existent game"""
        fake_game_id = str(uuid.uuid4())
        url = f'/api/v1/game/{fake_game_id}/bet/'
        data = {'action': 'call'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_bet_action_wrong_phase(self):
        """Test betting action in wrong game phase"""
        # This would require setting up a game in drawing phase
        game_id = self.create_sample_game()
        
        # First, move to drawing phase by calling
        self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
        
        # Now try to bet again (should be in drawing phase)
        url = f'/api/v1/game/{game_id}/bet/'
        data = {'action': 'call'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_bet_action_missing_required_fields(self):
        """Test betting action without required fields"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DrawActionTestCase(PokerGameAPITestCase):
    """Test cases for draw actions"""
    
    def setUp(self):
        super().setUp()
        # Create a game and move to drawing phase
        self.game_id = self.create_sample_game()
        # Call to move to drawing phase
        self.client.post(f'/api/v1/game/{self.game_id}/bet/', {'action': 'call'}, format='json')
    
    def test_draw_cards_success(self):
        """Test successful card drawing"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [0, 2, 4]}  # Discard 3 cards
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['playerHand']), 5)  # Should still have 5 cards
        # The cards at discarded indices should be different
    
    def test_draw_no_cards(self):
        """Test drawing zero cards (stand pat)"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': []}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_draw_all_cards(self):
        """Test drawing all 5 cards"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [0, 1, 2, 3, 4]}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['playerHand']), 5)
    
    def test_draw_invalid_indices(self):
        """Test drawing with invalid card indices"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [0, 5, 10]}  # Invalid indices
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_draw_negative_indices(self):
        """Test drawing with negative indices"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [-1, 0, 1]}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_draw_duplicate_indices(self):
        """Test drawing with duplicate indices"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [0, 1, 1, 2]}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_draw_too_many_cards(self):
        """Test drawing more than 5 cards"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {'discardIndices': [0, 1, 2, 3, 4, 5]}  # 6 indices
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_draw_game_not_found(self):
        """Test drawing cards on non-existent game"""
        fake_game_id = str(uuid.uuid4())
        url = f'/api/v1/game/{fake_game_id}/draw/'
        data = {'discardIndices': [0, 1]}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_draw_wrong_phase(self):
        """Test drawing cards in wrong game phase"""
        # Create a new game (should be in betting phase)
        new_game_id = self.create_sample_game()
        url = f'/api/v1/game/{new_game_id}/draw/'
        data = {'discardIndices': [0, 1]}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_draw_missing_required_fields(self):
        """Test drawing without required fields"""
        url = f'/api/v1/game/{self.game_id}/draw/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GameFlowTestCase(PokerGameAPITestCase):
    """Test cases for complete game flow scenarios"""
    
    def test_full_game_flow_player_wins(self):
        """Test complete game flow where player wins"""
        # Create game
        game_id = self.create_sample_game()
        
        # Betting phase - call
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
        self.assertEqual(response.data['phase'], 'drawing')
        
        # Drawing phase - stand pat
        response = self.client.post(f'/api/v1/game/{game_id}/draw/', {'discardIndices': []}, format='json')
        self.assertIn(response.data['phase'], ['showdown', 'finished'])
        
        # Game should be finished or in showdown
        if response.data['phase'] == 'finished':
            self.assertIsNotNone(response.data['winner'])
            self.assertIsNotNone(response.data['winningHand'])
    
    def test_full_game_flow_player_folds(self):
        """Test complete game flow where player folds immediately"""
        game_id = self.create_sample_game()
        
        # Fold immediately
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'fold'}, format='json')
        
        self.assertEqual(response.data['phase'], 'finished')
        self.assertIsNotNone(response.data['winner'])
        self.assertNotEqual(response.data['winner'], 'player')  # Player shouldn't win when folding
    
    def test_full_game_flow_with_raise(self):
        """Test game flow with raise action"""
        game_id = self.create_sample_game()
        
        # Raise
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'raise', 'amount': 50}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['currentBet'], 50)
        
        # Should still be in betting phase for opponents to respond
        self.assertEqual(response.data['phase'], 'betting')
    
    def test_multiple_betting_rounds(self):
        """Test multiple betting rounds"""
        game_id = self.create_sample_game()
        
        # First raise
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'raise', 'amount': 30}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # If still in betting phase, call to proceed
        if response.data['phase'] == 'betting':
            response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class ValidationTestCase(PokerGameAPITestCase):
    """Test cases for input validation and error handling"""
    
    def test_invalid_json_format(self):
        """Test handling of invalid JSON format"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        
        response = self.client.post(url, 'invalid json', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_empty_request_body(self):
        """Test handling of empty request body"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        
        response = self.client.post(url, '', content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_malformed_uuid_in_path(self):
        """Test handling of malformed UUID in path"""
        url = '/api/v1/game/not-a-uuid/bet/'
        data = {'action': 'call'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_extra_fields_ignored(self):
        """Test that extra fields in request are ignored"""
        game_id = self.create_sample_game()
        url = f'/api/v1/game/{game_id}/bet/'
        data = {
            'action': 'call',
            'extraField': 'should be ignored',
            'anotherExtra': 123
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EdgeCaseTestCase(PokerGameAPITestCase):
    """Test cases for edge cases and boundary conditions"""
    
    def test_game_state_after_completion(self):
        """Test accessing game state after game completion"""
        game_id = self.create_sample_game()
        
        # Complete the game by folding
        self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'fold'}, format='json')
        
        # Should still be able to access game state
        response = self.client.get(f'/api/v1/game/{game_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phase'], 'finished')
    
    def test_actions_after_game_completion(self):
        """Test that actions are not allowed after game completion"""
        game_id = self.create_sample_game()
        
        # Complete the game
        self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'fold'}, format='json')
        
        # Try to bet again
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Try to draw
        response = self.client.post(f'/api/v1/game/{game_id}/draw/', {'discardIndices': [0]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_concurrent_access_same_game(self):
        """Test concurrent access to same game (basic check)"""
        game_id = self.create_sample_game()
        
        # Simulate two simultaneous calls
        response1 = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
        response2 = self.client.get(f'/api/v1/game/{game_id}/')
        
        # Both should succeed (detailed concurrency handling would require more complex setup)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
    
    def test_maximum_raise_amount(self):
        """Test raising with maximum possible amount (all-in)"""
        game_id = self.create_sample_game()
        
        # Get current game state to know player's chips
        game_state = self.client.get(f'/api/v1/game/{game_id}/').data
        player_chips = game_state['playerChips']
        
        # Raise all remaining chips
        response = self.client.post(
            f'/api/v1/game/{game_id}/bet/', 
            {'action': 'raise', 'amount': player_chips}, 
            format='json'
        )
        
        # Should succeed or give appropriate error based on game rules
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST])


class ResponseFormatTestCase(PokerGameAPITestCase):
    """Test cases for response format validation"""
    
    def test_game_state_response_format(self):
        """Test that game state response has correct format"""
        game_id = self.create_sample_game()
        response = self.client.get(f'/api/v1/game/{game_id}/')
        
        data = response.data
        required_fields = [
            'gameId', 'phase', 'pot', 'playerHand', 'playerChips', 
            'opponents', 'canCall', 'canRaise', 'canFold', 'currentBet'
        ]
        
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")
        
        # Validate data types
        self.assertIsInstance(data['gameId'], str)
        self.assertIsInstance(data['phase'], str)
        self.assertIsInstance(data['pot'], int)
        self.assertIsInstance(data['playerHand'], list)
        self.assertIsInstance(data['playerChips'], int)
        self.assertIsInstance(data['opponents'], list)
        self.assertIsInstance(data['canCall'], bool)
        self.assertIsInstance(data['canRaise'], bool)
        self.assertIsInstance(data['canFold'], bool)
        self.assertIsInstance(data['currentBet'], int)
    
    def test_error_response_format(self):
        """Test that error responses have correct format"""
        response = self.client.get('/api/v1/game/invalid-uuid/')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Error format may vary based on DRF configuration
        # Basic check that it's a proper error response
        self.assertIn('error', response.data or str(response.content))


class PerformanceTestCase(PokerGameAPITestCase):
    """Basic performance test cases"""
    
    def test_multiple_games_creation(self):
        """Test creating multiple games in succession"""
        game_ids = []
        
        for i in range(10):
            response = self.client.post('/api/v1/game/')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            game_ids.append(response.data['gameId'])
        
        # All games should have unique IDs
        self.assertEqual(len(set(game_ids)), 10)
    
    def test_rapid_game_state_requests(self):
        """Test rapid consecutive game state requests"""
        game_id = self.create_sample_game()
        
        for i in range(5):
            response = self.client.get(f'/api/v1/game/{game_id}/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['gameId'], game_id)


# Integration test for complete API workflow
class IntegrationTestCase(PokerGameAPITestCase):
    """Integration tests for complete API workflows"""
    
    def test_complete_poker_game_workflow(self):
        """Test a complete poker game from start to finish"""
        # Step 1: Create new game
        response = self.client.post('/api/v1/game/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        game_id = response.data['gameId']
        self.assertEqual(response.data['phase'], 'betting')
        
        # Step 2: Check initial game state
        response = self.client.get(f'/api/v1/game/{game_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        initial_chips = response.data['playerChips']
        
        # Step 3: Make betting decision (call)
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'call'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phase'], 'drawing')
        
        # Step 4: Draw cards (discard some cards)
        response = self.client.post(f'/api/v1/game/{game_id}/draw/', {'discardIndices': [0, 4]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Step 5: Check final game state
        final_response = self.client.get(f'/api/v1/game/{game_id}/')
        self.assertEqual(final_response.status_code, status.HTTP_200_OK)
        
        # Game should be finished or in showdown
        self.assertIn(final_response.data['phase'], ['showdown', 'finished'])
        
        if final_response.data['phase'] == 'finished':
            # Should have winner and winning hand information
            self.assertIsNotNone(final_response.data['winner'])
            self.assertIsNotNone(final_response.data['winningHand'])
    
    def test_player_fold_workflow(self):
        """Test workflow where player folds immediately"""
        # Create game
        response = self.client.post('/api/v1/game/')
        game_id = response.data['gameId']
        
        # Player folds
        response = self.client.post(f'/api/v1/game/{game_id}/bet/', {'action': 'fold'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phase'], 'finished')
        
        # Verify game is properly concluded
        final_state = self.client.get(f'/api/v1/game/{game_id}/').data
        self.assertEqual(final_state['phase'], 'finished')
        self.assertIsNotNone(final_state['winner'])
        self.assertNotEqual(final_state['winner'], 'player')  # Player shouldn't win when folding