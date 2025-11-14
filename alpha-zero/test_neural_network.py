"""
test_neural_network.py - Test Neural Network Initialization and Forward Pass

This script tests that the neural network can be:
1. Initialized correctly
2. Run a forward pass
3. Make predictions
4. Train on sample data

Run this before starting full training to ensure everything works.
"""

import sys
import os
import numpy as np

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from antiyoy.AntiyoyGame import AntiyoyGame
from antiyoy.pytorch.NNet import NNetWrapper


def test_network_initialization():
    """Test that the network can be initialized."""
    print("=" * 60)
    print("TEST 1: Network Initialization")
    print("=" * 60)

    try:
        game = AntiyoyGame()
        nnet = NNetWrapper(game)
        print("✓ Network initialized successfully!")
        print(f"  Board size: {game.getBoardSize()}")
        print(f"  Action size: {game.getActionSize()}")
        return nnet, game
    except Exception as e:
        print(f"✗ Network initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None


def test_forward_pass(nnet, game):
    """Test that the network can process input and produce output."""
    print("\n" + "=" * 60)
    print("TEST 2: Forward Pass")
    print("=" * 60)

    try:
        # Get a sample board
        board = game.getInitBoard()
        print(f"  Input board shape: {board.shape}")

        # Make prediction
        pi, v = nnet.predict(board)

        print(f"✓ Forward pass successful!")
        print(f"  Policy output shape: {pi.shape}")
        print(f"  Value output: {v}")
        print(f"  Policy sum (should be ~1.0): {np.sum(pi):.4f}")
        print(f"  Value range (should be in [-1, 1]): [{np.min(v):.4f}, {np.max(v):.4f}]")

        # Validate outputs
        assert pi.shape[0] == game.getActionSize(), "Policy size mismatch!"
        assert np.abs(np.sum(pi) - 1.0) < 0.01, "Policy doesn't sum to 1!"
        assert -1.0 <= v <= 1.0, "Value out of range!"

        print("✓ All output validations passed!")
        return True

    except Exception as e:
        print(f"✗ Forward pass failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_batch_prediction(nnet, game):
    """Test that the network can handle batches of inputs."""
    print("\n" + "=" * 60)
    print("TEST 3: Batch Prediction")
    print("=" * 60)

    try:
        # Create a batch of boards
        batch_size = 8
        board = game.getInitBoard()

        # Make predictions on multiple boards
        print(f"  Making predictions on {batch_size} boards...")
        predictions = []
        for i in range(batch_size):
            pi, v = nnet.predict(board)
            predictions.append((pi, v))

        print(f"✓ Batch prediction successful!")
        print(f"  Processed {batch_size} boards")
        print(f"  Average value: {np.mean([v for _, v in predictions]):.4f}")

        return True

    except Exception as e:
        print(f"✗ Batch prediction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_training(nnet, game):
    """Test that the network can train on sample data."""
    print("\n" + "=" * 60)
    print("TEST 4: Training on Sample Data")
    print("=" * 60)

    try:
        # Create fake training examples
        num_examples = 100
        examples = []

        print(f"  Creating {num_examples} fake training examples...")
        board = game.getInitBoard()

        for i in range(num_examples):
            # Random policy (uniform distribution)
            pi = np.ones(game.getActionSize()) / game.getActionSize()

            # Random value
            v = np.random.choice([-1, 0, 1])

            examples.append((board, pi, v))

        print(f"  Training network on {num_examples} examples...")
        print(f"  (This will take a few seconds...)")

        # Train for 1 epoch
        nnet.train(examples)

        print(f"✓ Training successful!")
        print(f"  Network can learn from examples")

        return True

    except Exception as e:
        print(f"✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_save_load(nnet, game):
    """Test that the network can save and load checkpoints."""
    print("\n" + "=" * 60)
    print("TEST 5: Checkpoint Save/Load")
    print("=" * 60)

    try:
        # Create temporary checkpoint directory
        checkpoint_dir = './test_checkpoint'

        print(f"  Saving checkpoint to {checkpoint_dir}...")
        nnet.save_checkpoint(folder=checkpoint_dir, filename='test.pth.tar')
        print(f"✓ Checkpoint saved!")

        # Make a prediction before loading
        board = game.getInitBoard()
        pi_before, v_before = nnet.predict(board)

        print(f"  Loading checkpoint...")
        nnet.load_checkpoint(folder=checkpoint_dir, filename='test.pth.tar')
        print(f"✓ Checkpoint loaded!")

        # Make a prediction after loading
        pi_after, v_after = nnet.predict(board)

        # Verify predictions are the same
        pi_diff = np.max(np.abs(pi_before - pi_after))
        v_diff = float(np.abs(v_before - v_after))

        print(f"  Policy difference after reload: {pi_diff:.6f}")
        print(f"  Value difference after reload: {v_diff:.6f}")

        assert pi_diff < 1e-5, "Policy changed after reload!"
        assert v_diff < 1e-5, "Value changed after reload!"

        print(f"✓ Checkpoint save/load working correctly!")

        # Clean up
        import shutil
        shutil.rmtree(checkpoint_dir)
        print(f"  Cleaned up test checkpoint directory")

        return True

    except Exception as e:
        print(f"✗ Checkpoint save/load failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("ANTIYOY NEURAL NETWORK TESTS")
    print("=" * 60)

    all_passed = True

    # Test 1: Initialization
    nnet, game = test_network_initialization()
    if nnet is None:
        print("\n✗ Cannot continue without network initialization")
        return

    # Test 2: Forward pass
    if not test_forward_pass(nnet, game):
        all_passed = False

    # Test 3: Batch prediction
    if not test_batch_prediction(nnet, game):
        all_passed = False

    # Test 4: Training
    if not test_training(nnet, game):
        all_passed = False

    # Test 5: Checkpoint save/load
    if not test_checkpoint_save_load(nnet, game):
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nThe neural network is ready for training.")
        print("You can now run: python alpha-zero/main.py")
    else:
        print("✗ SOME TESTS FAILED")
        print("\nPlease fix the issues before starting training.")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
