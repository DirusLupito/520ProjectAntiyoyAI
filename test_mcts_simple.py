#!/usr/bin/env python3
"""Test MCTS with the fixed game logic"""

import sys
import numpy as np
import logging
sys.path.insert(0, 'alpha-zero')

from antiyoy.AntiyoyGame import AntiyoyGame
from MCTS import MCTS

# Enable logging to see MCTS stats
logging.basicConfig(level=logging.INFO, format='%(message)s')

class DummyNNet:
    """Dummy neural network that returns random policy and value"""
    def predict(self, board):
        # Return uniform policy and neutral value
        policy = np.ones(973) / 973.0
        value = 0.0
        return policy, value

class Args:
    """Arguments for MCTS"""
    def __init__(self):
        self.numMCTSSims = 1000  # Many simulations to test terminal reaching
        self.cpuct = 1.0

# Create game and MCTS
game = AntiyoyGame()
nnet = DummyNNet()
args = Args()
mcts = MCTS(game, nnet, args)

# Get initial board
board = game.getInitBoard()

print("=== Testing MCTS ===")
print(f"Running {args.numMCTSSims} MCTS simulations...")

# Run MCTS
try:
    pi = mcts.getActionProb(board, temp=1)
    print(f"✓ MCTS completed successfully!")
    print(f"  Action probabilities computed: {len(pi)} actions")
    print(f"  Max probability: {max(pi):.4f}")
    print(f"  Non-zero actions: {sum(1 for p in pi if p > 0)}")
except RecursionError as e:
    print(f"✗ MCTS failed with RecursionError: {e}")
except Exception as e:
    print(f"✗ MCTS failed with {type(e).__name__}: {e}")
