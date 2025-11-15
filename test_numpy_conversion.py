#!/usr/bin/env python3
"""Test that resources are preserved through numpy conversion"""

import sys
sys.path.insert(0, 'alpha-zero')

from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction
from antiyoy.AntiyoyLogic import Board

# Create factions
faction1 = Faction(name="Player 1", color="Red", playerType="ai", aiType="alphazero")
faction2 = Faction(name="Player 2", color="Blue", playerType="ai", aiType="donothing")

# Generate scenario
scenario = generateRandomScenario(
    dimension=6,
    targetNumberOfLandTiles=20,
    factions=[faction1, faction2],
    initialProvinceSize=3,
    randomSeed=42
)

print("=== Original Scenario ===")
for i, faction in enumerate(scenario.factions):
    print(f"Faction {i+1}: {faction.name}")
    for province in faction.provinces:
        print(f"  Province: {len(province.tiles)} tiles, {province.resources} resources")

# Convert to Board and then to numpy
print("\n=== Converting to numpy and back ===")
board = Board(scenario=scenario, current_player=1)
numpy_board = board.get_numpy_board()

# Reconstruct from numpy
reconstructed_board = Board.from_numpy(numpy_board, current_player=1)

print("\n=== Reconstructed Scenario ===")
for i, faction in enumerate(reconstructed_board.scenario.factions):
    print(f"Faction {i+1}: {faction.name}")
    for province in faction.provinces:
        print(f"  Province: {len(province.tiles)} tiles, {province.resources} resources")

# Check valid moves
print("\n=== Checking valid moves ===")
valid_moves = reconstructed_board.get_valid_moves_vector(debug=True)
num_valid = int(valid_moves.sum())
print(f"Total valid moves: {num_valid}")
