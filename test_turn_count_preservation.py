#!/usr/bin/env python3
"""Test if turn_count is preserved through MCTS getNextState calls"""

import sys
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board

game = AntiyoyGame()
board = game.getInitBoard()

print("=== Testing turn_count Preservation ===")

# Initial state
b = Board.from_numpy(board, 1)
print(f"Initial turn_count: {b.turn_count}")

# Take a build action (should succeed and force END_TURN with MAX_ACTIONS_PER_TURN=1)
valid = game.getValidMoves(board, 1)
build_actions = [i for i in range(720, 720+252) if valid[i] > 0]
if build_actions:
    action = build_actions[0]
    print(f"\nTaking build action {action}...")

    board2, player2 = game.getNextState(board, 1, action)
    b2 = Board.from_numpy(board2, 1)
    print(f"After action: turn_count={b2.turn_count}, player={player2}")

    # Take another action
    valid2 = game.getValidMoves(board2, player2)
    # Convert to canonical form like MCTS does
    board2_canon = game.getCanonicalForm(board2, player2)
    valid2_canon = game.getValidMoves(board2_canon, 1)
    build_actions2 = [i for i in range(720, 720+252) if valid2_canon[i] > 0]

    if build_actions2:
        action2 = build_actions2[0]
        print(f"\nTaking another build action {action2}...")

        board3, player3 = game.getNextState(board2_canon, 1, action2)
        b3 = Board.from_numpy(board3, 1)
        print(f"After 2nd action: turn_count={b3.turn_count}, player={player3}")

        # Check turn_count incremented
        if b3.turn_count > b.turn_count:
            print(f"\n✓ turn_count incremented correctly: {b.turn_count} → {b3.turn_count}")
        else:
            print(f"\n✗ turn_count NOT incrementing: {b.turn_count} → {b3.turn_count}")
            print("This explains why MCTS games never end!")

        # Check debug counters
        from antiyoy.AntiyoyLogic import Board
        if hasattr(Board, '_forced_end_turn_count'):
            print(f"\nForced END_TURN count: {Board._forced_end_turn_count}")
        if hasattr(Board, '_action_stats'):
            stats = Board._action_stats
            print(f"Actions: total={stats['total']}, failed={stats['failed']}, end_turn={stats['end_turn']}")
else:
    print("No build actions available")
