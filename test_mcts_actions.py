#!/usr/bin/env python3
"""Test what actions MCTS is choosing and why games don't end"""

import sys
import numpy as np
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.AntiyoyLogic import Board
from MCTS import MCTS

class DummyNNet:
    def predict(self, board):
        policy = np.ones(973) / 973.0
        value = 0.0
        return policy, value

class Args:
    def __init__(self):
        self.numMCTSSims = 5
        self.cpuct = 1.0

game = AntiyoyGame()
nnet = DummyNNet()
args = Args()
mcts = MCTS(game, nnet, args)

board = game.getInitBoard()

print("=== Testing MCTS Action Selection ===")
print(f"Initial turn_count: {Board.from_numpy(board, 1).turn_count}")

# Run one MCTS iteration
print("\nRunning MCTS...")
pi = mcts.getActionProb(board, temp=1)

# Check action stats
if hasattr(Board, '_action_stats'):
    stats = Board._action_stats
    print(f"\n=== Action Statistics ===")
    print(f"Total actions attempted: {stats['total']}")
    print(f"Failed actions: {stats['failed']}")
    print(f"END_TURN actions: {stats['end_turn']}")
    print(f"Success rate: {(stats['total'] - stats['failed']) / stats['total'] * 100:.1f}%")

    if stats['failed'] > stats['total'] * 0.5:
        print("\n⚠️  WARNING: More than 50% of actions are failing!")
        print("This will prevent turn_count from incrementing properly.")
