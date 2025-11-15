"""
test_agent.py - Test script for AlphaZero agent

This script demonstrates how to use the AlphaZero agent and tests
that it can load a trained model and make decisions.

Usage:
    python3 ai/alphaZeroAgent/test_agent.py

Note: You need to have trained a model first using alpha-zero/main.py
"""

import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

from ai.alphaZeroAgent import AlphaZeroAgent
from logic.Scenario import generateRandomScenario
from logic.Faction import Faction


def test_agent_initialization():
    """Test that agent can be created and checkpoint loaded."""
    print("=" * 60)
    print("TEST 1: Agent Initialization")
    print("=" * 60)

    try:
        agent = AlphaZeroAgent(
            checkpoint_folder='alpha-zero/temp',
            checkpoint_file='best.pth.tar',
            use_mcts=False,  # Fast mode for testing
            num_mcts_sims=25
        )
        print("✓ Agent initialized successfully!")
        return agent
    except FileNotFoundError as e:
        print(f"✗ Failed to load checkpoint: {e}")
        print("\nTo train a model, run:")
        print("  cd alpha-zero")
        print("  python3 main.py")
        print("\nThis will create alpha-zero/temp/best.pth.tar")
        return None
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_agent_playturn(agent):
    """Test that agent can generate actions for a turn."""
    print("\n" + "=" * 60)
    print("TEST 2: Generate Actions")
    print("=" * 60)

    # Create a simple test scenario
    faction1 = Faction(name="Player 1", color="red", playerType="AI")
    faction2 = Faction(name="Player 2", color="blue", playerType="AI")
    factions = [faction1, faction2]

    print("Creating test scenario...")
    scenario = generateRandomScenario(
        dimension=6,
        targetNumberOfLandTiles=20,
        factions=factions,
        initialProvinceSize=3,
        randomSeed=42  # Fixed seed for reproducibility
    )

    # Give factions some starting resources
    for faction in scenario.factions:
        for province in faction.provinces:
            province.resources = 30

    print("Scenario created successfully!")
    print(f"  Factions: {len(scenario.factions)}")
    print(f"  Active provinces: {sum(len([p for p in f.provinces if p.active]) for f in scenario.factions)}")

    # Test agent on first faction
    test_faction = scenario.factions[0]
    print(f"\nGenerating actions for {test_faction.name}...")

    try:
        actions = agent.playTurn(scenario, test_faction)
        print(f"✓ Agent generated {len(actions)} actions")

        if len(actions) > 0:
            print("\nActions:")
            for i, (action, province) in enumerate(actions):
                print(f"  {i+1}. {action} (province: {province})")
        else:
            print("\nNote: Agent chose to end turn immediately (no actions)")
            print("This is normal for untrained or early-training models")

        return True
    except Exception as e:
        print(f"✗ Failed to generate actions: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mcts_mode(agent):
    """Test agent with MCTS enabled."""
    print("\n" + "=" * 60)
    print("TEST 3: MCTS Mode (Optional)")
    print("=" * 60)

    print("Creating agent with MCTS...")
    try:
        mcts_agent = AlphaZeroAgent(
            checkpoint_folder='alpha-zero/temp',
            checkpoint_file='best.pth.tar',
            use_mcts=True,  # Enable MCTS
            num_mcts_sims=10  # Small number for quick test
        )
        print("✓ MCTS agent initialized successfully!")
        print("Note: MCTS mode is slower but produces stronger play")
        return True
    except Exception as e:
        print(f"✗ Failed to create MCTS agent: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ALPHAZERO AGENT TEST SUITE")
    print("=" * 60)

    # Test 1: Initialization
    agent = test_agent_initialization()
    if agent is None:
        print("\n" + "=" * 60)
        print("TESTS FAILED")
        print("=" * 60)
        print("\nCannot proceed without a trained checkpoint.")
        print("Please train a model first using:")
        print("  cd alpha-zero && python3 main.py")
        return

    # Test 2: Generate actions
    success = test_agent_playturn(agent)
    if not success:
        print("\n" + "=" * 60)
        print("TESTS FAILED")
        print("=" * 60)
        return

    # Test 3: MCTS mode (optional)
    test_mcts_mode(agent)

    # Summary
    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)
    print("\nThe AlphaZero agent is ready to use!")
    print("\nNext steps:")
    print("  1. Integrate agent into your game loop")
    print("  2. Test against other AI agents")
    print("  3. Continue training for stronger play")
    print("\nSee ai/alphaZeroAgent/README.md for usage examples")


if __name__ == "__main__":
    main()
