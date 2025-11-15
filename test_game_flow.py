#!/usr/bin/env python3
"""
Simulate the exact game flow to find where resources go to 0
"""

from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction

# Create factions (same as in a real game)
faction1 = Faction(name="Human", color="Red", playerType="human", aiType=None)
faction2 = Faction(name="AlphaZero", color="Blue", playerType="ai", aiType="alphazero")
factions = [faction1, faction2]

# Generate scenario
print("=== Generating scenario ===")
scenario = generateRandomScenario(
    dimension=6,
    targetNumberOfLandTiles=20,
    factions=factions,
    initialProvinceSize=3,
    randomSeed=42
)

print("\n=== Initial state (before any turns) ===")
for faction in scenario.factions:
    print(f"\n{faction.name}:")
    for province in faction.provinces:
        print(f"  Tiles: {len(province.tiles)}, Resources: {province.resources}, Active: {province.active}")

# Simulate: Human player plays first (Faction 1)
print("\n=== Human's Turn (Faction 1) ===")
print(f"Current faction to play: {scenario.getFactionToPlay().name}")
current_faction = scenario.factions[0]
for province in current_faction.provinces:
    print(f"  Tiles: {len(province.tiles)}, Resources: {province.resources}, Active: {province.active}")

# Human does nothing, ends turn
print("\n=== Human ends turn - calling advanceTurn() ===")
turnAdvanceActions = scenario.advanceTurn()
print(f"Number of turn advance actions: {len(turnAdvanceActions)}")

# Now it's AI's turn
print("\n=== AI's Turn (Faction 2) ===")
print(f"Current faction to play: {scenario.getFactionToPlay().name}")
ai_faction = scenario.getFactionToPlay()

# Check province state BEFORE calling the AI agent
for province in ai_faction.provinces:
    print(f"  BEFORE AI plays - Tiles: {len(province.tiles)}, Resources: {province.resources}, Active: {province.active}")

# Try to get the agent (this will fail if no checkpoint exists, but that's ok)
print("\n=== Attempting to load AlphaZero agent ===")
try:
    # Import the playTurn function which will load the agent
    from ai.alphaZeroAgent.AlphaZeroAgent import playTurn as alphaZeroPlayTurn

    print("\n=== Calling AlphaZero playTurn() ===")
    actions = alphaZeroPlayTurn(scenario, ai_faction)

    print(f"\n=== AI returned {len(actions)} actions ===")
except Exception as e:
    print(f"Error with AlphaZero agent: {e}")
    import traceback
    traceback.print_exc()

# Check province state AFTER calling the AI agent
print("\n=== After AI plays ===")
for province in ai_faction.provinces:
    print(f"  AFTER AI plays - Tiles: {len(province.tiles)}, Resources: {province.resources}, Active: {province.active}")
