"""
AntiyoyGame.py - Game interface implementation for Antiyoy

This module implements the Game interface required by alpha-zero-general
for the Antiyoy game.
"""

import numpy as np
import sys
import os

# Add the azg directory to the path to import Game base class
azg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'azg')
sys.path.append(azg_path)

from Game import Game
from .AntiyoyLogic import Board


class AntiyoyGame(Game):
    """
    Implementation of the Game interface for Antiyoy.

    This class provides the interface between the alpha-zero-general framework
    and the Antiyoy game logic.

    Game rules:
    - 6x6 hexagonal board
    - 2 players (factions)
    - Players take turns making multiple actions (moves/builds) then ending turn
    - Win by being the last faction with active provinces
    - Provinces need >= 2 tiles to be active
    """

    def __init__(self):
        """Initialize the game."""
        self.height = Board.HEIGHT
        self.width = Board.WIDTH
        self.num_channels = Board.NUM_CHANNELS  # Now 23 (includes action counter)
        self.action_size = Board.ACTION_SIZE

    def getInitBoard(self):
        """
        Returns:
            startBoard: numpy array representing the initial board state
        """
        b = Board()
        return b.get_numpy_board()

    def getBoardSize(self):
        """
        Returns:
            (num_channels, height, width): tuple of board dimensions
        """
        return (self.num_channels, self.height, self.width)

    def getActionSize(self):
        """
        Returns:
            actionSize: int, number of all possible actions
        """
        return self.action_size

    def getNextState(self, board, player, action):
        """
        Input:
            board: current board (numpy array)
            player: current player (1 or -1)
            action: action taken by current player

        Returns:
            nextBoard: board after applying action (numpy array)
            nextPlayer: player who plays in the next turn (1 or -1)

        Note: For multi-action turns, if the action is not "end turn",
        the next player is the same as the current player.
        """
        # Create a Board from the current state
        b = self._board_from_numpy(board, player)

        # Store the current faction index before applying action
        faction_before = b.scenario.indexOfFactionToPlay

        # Apply the action
        success = b.apply_action(action)

        if not success:
            # Invalid action - return same board and player
            return (board, player)

        # Get the updated board state
        next_board = b.get_numpy_board()

        # Check if the faction changed (turn ended)
        # This handles both explicit end-turn and forced end-turn after MAX_ACTIONS_PER_TURN
        faction_after = b.scenario.indexOfFactionToPlay

        if faction_before != faction_after:
            # Turn ended, switch to other player
            next_player = -player
        else:
            # Same player continues (multi-action turn)
            next_player = player

        return (next_board, next_player)

    def getValidMoves(self, board, player, debug=False):
        """
        Input:
            board: current board (numpy array)
            player: current player (1 or -1)
            debug: If True, print debug information

        Returns:
            validMoves: binary numpy array of length getActionSize(), where
                        validMoves[i] = 1 if action i is valid, 0 otherwise
        """
        b = self._board_from_numpy(board, player)
        return b.get_valid_moves_vector(debug=debug)

    def getGameEnded(self, board, player):
        """
        Input:
            board: current board (numpy array)
            player: current player (1 or -1)

        Returns:
            r: 0 if game has not ended.
               1 if player won.
               -1 if player lost.
               small non-zero value (e.g., 1e-4) for draw.
        """
        b = self._board_from_numpy(board, player)
        return b.check_game_ended(player)

    def getCanonicalForm(self, board, player):
        """
        Input:
            board: current board (numpy array)
            player: current player (1 or -1)

        Returns:
            canonicalBoard: canonical form of the board from the perspective
                            of player 1. If player == 1, returns board as-is.
                            If player == -1, swaps the player channels.
        """
        if player == 1:
            return board

        # Swap player 1 and player 2 channels
        canonical = np.copy(board)

        # Swap ownership channels (0 and 1)
        canonical[0], canonical[1] = board[1].copy(), board[0].copy()

        # Swap soldier channels (3-6 with 7-10)
        for i in range(4):
            canonical[3 + i], canonical[7 + i] = board[7 + i].copy(), board[3 + i].copy()

        # Swap resource channels (18 and 19)
        canonical[18], canonical[19] = board[19].copy(), board[18].copy()

        # Swap income channels (20 and 21)
        canonical[20], canonical[21] = board[21].copy(), board[20].copy()

        return canonical

    def getSymmetries(self, board, pi):
        """
        Input:
            board: current board (numpy array)
            pi: policy vector of size getActionSize()

        Returns:
            symmForms: a list of [(board, pi)] where each tuple is a symmetrical
                       form of the board and the corresponding pi vector.

        Note: Hexagonal grids have complex symmetries (rotations and reflections).
        For now, we return only the original board (no symmetries).
        TODO: Implement hex grid symmetries if needed for better training.
        """
        # No symmetries for now
        return [(board, pi)]

    def stringRepresentation(self, board):
        """
        Input:
            board: current board (numpy array)

        Returns:
            boardString: string representation of the board.
                         Used for MCTS hashing.
        """
        # Convert to bytes for hashing
        return board.tobytes()

    def _board_from_numpy(self, numpy_board, player):
        """
        Helper method to create a Board object from a numpy array.

        Args:
            numpy_board: numpy array representing the board
            player: current player (1 or -1)

        Returns:
            Board object
        """
        return Board.from_numpy(numpy_board, player)

    def display(self, board):
        """
        Display the board in a human-readable format.

        Args:
            board: numpy array representing the board
        """
        print("\n" + "=" * 50)
        print("ANTIYOY BOARD (6x6 Hex Grid)")
        print("=" * 50)

        # Display ownership
        print("\nOwnership (P1=1, P2=2, water=W, neutral=.):")
        for row in range(self.height):
            # Add offset for hexagonal display
            if row % 2 == 1:
                print("  ", end="")

            for col in range(self.width):
                if board[2, row, col] > 0:  # Water
                    print(" W ", end="")
                elif board[0, row, col] > 0:  # Player 1
                    print(" 1 ", end="")
                elif board[1, row, col] > 0:  # Player 2
                    print(" 2 ", end="")
                else:
                    print(" . ", end="")
            print()

        # Display units (simplified)
        print("\nUnits (S=soldier tier, C=capital, F=farm, T=tower, t=tree):")
        for row in range(self.height):
            if row % 2 == 1:
                print("  ", end="")

            for col in range(self.width):
                unit_char = " . "

                # Check for soldiers
                for tier in range(1, 5):
                    if board[3 + tier - 1, row, col] > 0:  # P1 soldier
                        unit_char = f"S{tier} "
                        break
                    if board[7 + tier - 1, row, col] > 0:  # P2 soldier
                        unit_char = f"s{tier} "
                        break

                # Check for structures
                if board[11, row, col] > 0:  # Capital
                    unit_char = " C "
                elif board[12, row, col] > 0:  # Farm
                    unit_char = " F "
                elif board[13, row, col] > 0:  # Tower1
                    unit_char = " T1"
                elif board[14, row, col] > 0:  # Tower2
                    unit_char = " T2"
                elif board[15, row, col] > 0:  # Tree
                    unit_char = " t "
                elif board[16, row, col] > 0:  # Gravestone
                    unit_char = " g "

                print(unit_char, end="")
            print()

        # Display resources
        p1_resources = board[18, 0, 0] if board[0, 0, 0] > 0 else 0
        p2_resources = board[19, 0, 0] if board[1, 0, 0] > 0 else 0
        print(f"\nResources (normalized): P1={p1_resources:.2f}, P2={p2_resources:.2f}")

        print("=" * 50 + "\n")
