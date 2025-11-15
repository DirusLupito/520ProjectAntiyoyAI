#!/usr/bin/env python3
"""Test if check_game_ended is working correctly during MCTS simulation"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Testing Game Ending During Simulation ===")

# Simulate a long game by repeatedly taking END_TURN
for turn in range(55):
    result = game.getGameEnded(board, 1)

    if result != 0:
        print(f"✓ Game ended at turn {turn}: result={result}")
        break

    # Take END_TURN action
    end_turn_action = game.getActionSize() - 1
    board, player = game.getNextState(board, 1, end_turn_action)
    board = game.getCanonicalForm(board, player)

    if turn % 10 == 0 or turn >= 48:
        b = Board.from_numpy(board, 1)
        print(f"Turn {turn}: turn_count={b.turn_count}, game_ended={result}")
else:
    print(f"✗ Game did NOT end after 55 turns!")
    b = Board.from_numpy(board, 1)
    print(f"Final turn_count: {b.turn_count}")
    result = game.getGameEnded(board, 1)
    print(f"Final getGameEnded result: {result}")
