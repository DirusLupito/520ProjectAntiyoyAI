#!/usr/bin/env python3
"""
Quick test to check province resources initialization
"""

from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction

# Create factions
faction1 = Faction(name="Player 1", color="Red", playerType="ai", aiType="alphazero")
faction2 = Faction(name="Player 2", color="Blue", playerType="ai", aiType="alphazero")
factions = [faction1, faction2]

# Generate scenario
print("Generating scenario...")
scenario = generateRandomScenario(
    dimension=6,
    targetNumberOfLandTiles=20,
    factions=factions,
    initialProvinceSize=3,
    randomSeed=42
)

print("\n=== Initial Province State ===")
for i, faction in enumerate(scenario.factions):
    print(f"\nFaction {i+1}: {faction.name}")
    for j, province in enumerate(faction.provinces):
        print(f"  Province {j+1}:")
        print(f"    Tiles: {len(province.tiles)}")
        print(f"    Resources: {province.resources}")
        print(f"    Active: {province.active}")
        print(f"    Income: {province.computeIncome()}")

print("\n=== After advanceTurn() ===")
# Advance turn to see what happens
scenario.advanceTurn()

for i, faction in enumerate(scenario.factions):
    print(f"\nFaction {i+1}: {faction.name}")
    for j, province in enumerate(faction.provinces):
        print(f"  Province {j+1}:")
        print(f"    Tiles: {len(province.tiles)}")
        print(f"    Resources: {province.resources}")
        print(f"    Active: {province.active}")
        print(f"    Income: {province.computeIncome()}")
