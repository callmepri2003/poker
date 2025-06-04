import uuid
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import Http404
from django.core.exceptions import ValidationError

from .models import Game
from .serializers import GameStateSerializer, BetActionSerializer, DrawActionSerializer
from .services import GameService


class GameViewSet(viewsets.ViewSet):
    """ViewSet for poker game operations"""
    
    def create(self, request):
        """Create a new poker game"""
        try:
            game = GameService.create_new_game()
            serializer = GameStateSerializer(game)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': 'Failed to create game', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, pk=None):
        """Get current game state"""
        try:
            # Validate UUID format
            uuid.UUID(pk)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid game ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            game = GameService.get_game_state(pk)
            serializer = GameStateSerializer(game)
            return Response(serializer.data)
        except ValueError:
            return Response(
                {'error': 'Game not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def bet(self, request, pk=None):
        """Process betting action"""
        try:
            # Validate UUID format
            uuid.UUID(pk)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid game ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            game = GameService.get_game_state(pk)
        except ValueError:
            return Response(
                {'error': 'Game not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request data
        serializer = BetActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid bet action', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if game is in correct phase
        if game.phase != 'betting':
            return Response(
                {'error': 'Cannot bet in current game phase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if game is finished
        if game.phase == 'finished':
            return Response(
                {'error': 'Game is already finished'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            action = serializer.validated_data['action']
            amount = serializer.validated_data.get('amount')
            
            updated_game = GameService.process_bet_action(game, action, amount)
            response_serializer = GameStateSerializer(updated_game)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to process bet action', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def draw(self, request, pk=None):
        """Process card drawing action"""
        try:
            # Validate UUID format
            uuid.UUID(pk)
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid game ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            game = GameService.get_game_state(pk)
        except ValueError:
            return Response(
                {'error': 'Game not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Validate request data
        serializer = DrawActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid draw action', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if game is in correct phase
        if game.phase != 'drawing':
            return Response(
                {'error': 'Cannot draw in current game phase'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if game is finished
        if game.phase == 'finished':
            return Response(
                {'error': 'Game is already finished'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            discard_indices = serializer.validated_data['discardIndices']
            
            updated_game = GameService.process_draw_action(game, discard_indices)
            response_serializer = GameStateSerializer(updated_game)
            return Response(response_serializer.data)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to process draw action', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )