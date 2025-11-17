"""
NNet.py - Neural Network Wrapper for Training and Prediction

This module provides a wrapper around the AntiyoyNNet that handles:
1. Training on self-play examples
2. Making predictions during MCTS search
3. Saving and loading model checkpoints
4. Loss computation and optimization

The wrapper implements the NeuralNet interface required by alpha-zero-general.
"""

import os
import sys
import time

import numpy as np
from tqdm import tqdm

# Add paths for imports
sys.path.append('../../../')
from azg.utils import *
from azg.NeuralNet import NeuralNet

import torch
import torch.optim as optim

from .AntiyoyNNet import AntiyoyNNet as nnet


# ===================================================================
# HYPERPARAMETERS
# These can be tuned for better performance
# ===================================================================
args = dotdict({
    # Learning rate for Adam optimizer
    # Lower = more stable but slower convergence
    # Higher = faster but may be unstable
    # Typical range: 0.0001 - 0.01
    'lr': 0.001,

    # Dropout rate for regularization
    # Prevents overfitting by randomly dropping connections during training
    # 0.0 = no dropout, 1.0 = drop everything (don't use)
    # Typical range: 0.2 - 0.5
    'dropout': 0.2,

    # Number of training epochs per learning iteration
    # More epochs = better convergence but slower
    # Typical range: 5 - 20
    'epochs': 10,

    # Batch size for training
    # Larger = more stable gradients but uses more memory
    # Smaller = more updates but noisier gradients
    # Typical range: 32 - 256
    'batch_size': 128,

    # Use GPU if available
    # GPU training is much faster for neural networks
    'cuda': torch.cuda.is_available(),

    # Number of convolutional filters (network width)
    # More = more capacity but slower and may overfit
    # Typical range: 128 - 512
    'num_channels': 128,

    # Number of residual blocks (network depth)
    # More = can learn more complex patterns but slower
    # Typical range: 3 - 15
    'num_res_blocks': 3,
})


class NNetWrapper(NeuralNet):
    """
    Wrapper class for the Antiyoy neural network.

    This class handles all interactions between the alpha-zero-general
    training framework and the PyTorch neural network.

    Key responsibilities:
    1. Initialize the network and move to GPU if available
    2. Train the network on self-play examples
    3. Make predictions during MCTS search
    4. Save and load model checkpoints
    """

    def __init__(self, game):
        """
        Initialize the neural network wrapper.

        Args:
            game: AntiyoyGame instance (used to get board/action sizes)
        """
        # Create the neural network
        self.nnet = nnet(game, args)

        # Get board and action dimensions
        board_dims = game.getBoardSize()
        if len(board_dims) == 3:
            self.num_channels, self.board_y, self.board_x = board_dims
        else:
            self.board_x, self.board_y = board_dims
            self.num_channels = 1

        self.action_size = game.getActionSize()

        # Move network to GPU if available
        if args.cuda:
            self.nnet.cuda()
            print("Using CUDA (GPU acceleration)")
        else:
            print("Using CPU (consider using GPU for faster training)")

    def train(self, examples):
        """
        Train the neural network on self-play examples.

        This is called after each iteration of self-play to improve the network.
        The network learns to:
        1. Predict good moves (policy head) based on what MCTS found
        2. Evaluate positions (value head) based on game outcomes

        Args:
            examples: List of training examples, each is tuple (board, pi, v) where:
                     - board: numpy array of board state
                     - pi: MCTS-derived policy (probability distribution over actions)
                     - v: Game outcome from this position (+1, 0, or -1)

        The training process:
        1. For each epoch:
           a. Shuffle and batch the examples
           b. For each batch:
              - Compute network predictions
              - Calculate loss (how wrong the predictions are)
              - Update weights via backpropagation
        """

        # Create optimizer (Adam is standard for neural networks)
        # Adam adapts learning rate per parameter for better convergence
        optimizer = optim.Adam(self.nnet.parameters(), lr=args.lr)

        # Train for multiple epochs
        for epoch in range(args.epochs):
            print(f'EPOCH ::: {epoch + 1}/{args.epochs}')

            # Set network to training mode (enables dropout, batch norm training)
            self.nnet.train()

            # Track average losses for monitoring
            pi_losses = AverageMeter()  # Policy loss
            v_losses = AverageMeter()   # Value loss

            # Calculate number of batches
            batch_count = int(len(examples) / args.batch_size)

            # Progress bar for visual feedback
            t = tqdm(range(batch_count), desc='Training Net')

            for _ in t:
                # ===================================================================
                # SAMPLE BATCH
                # Randomly sample a batch of examples for training
                # Random sampling helps prevent overfitting to order of examples
                # ===================================================================
                sample_ids = np.random.randint(len(examples), size=args.batch_size)
                boards, pis, vs = list(zip(*[examples[i] for i in sample_ids]))

                # Convert to PyTorch tensors
                boards = torch.FloatTensor(np.array(boards).astype(np.float64))
                target_pis = torch.FloatTensor(np.array(pis))
                target_vs = torch.FloatTensor(np.array(vs).astype(np.float64))

                # Move to GPU if available
                if args.cuda:
                    boards = boards.contiguous().cuda()
                    target_pis = target_pis.contiguous().cuda()
                    target_vs = target_vs.contiguous().cuda()

                # ===================================================================
                # FORWARD PASS
                # Compute network predictions
                # ===================================================================
                out_pi, out_v = self.nnet(boards)

                # ===================================================================
                # COMPUTE LOSS
                # Loss measures how wrong the predictions are
                # We want to minimize this loss
                # ===================================================================
                l_pi = self.loss_pi(target_pis, out_pi)  # Policy loss
                l_v = self.loss_v(target_vs, out_v)      # Value loss

                # Total loss with weighted policy loss
                # Weighting policy loss more heavily encourages sharper predictions
                # policy_weight > 1.0 makes network focus more on matching MCTS policies
                policy_weight = 1.5  # Try 1.5-2.0 for more policy emphasis
                total_loss = policy_weight * l_pi + l_v

                # ===================================================================
                # BACKWARD PASS
                # Compute gradients and update weights
                # ===================================================================

                # Clear previous gradients
                optimizer.zero_grad()

                # Compute gradients via backpropagation
                total_loss.backward()

                # Update network weights
                optimizer.step()

                # ===================================================================
                # RECORD STATISTICS
                # Track losses for monitoring training progress
                # ===================================================================
                pi_losses.update(l_pi.item(), boards.size(0))
                v_losses.update(l_v.item(), boards.size(0))

                # Update progress bar with current losses
                t.set_postfix(Loss_pi=pi_losses, Loss_v=v_losses)

            # Print epoch summary
            print(f'Epoch {epoch + 1} complete - Policy Loss: {pi_losses}, Value Loss: {v_losses}')

    def predict(self, board):
        """
        Make a prediction for a single board position.

        This is called during MCTS search to evaluate positions and guide exploration.

        Args:
            board: numpy array representing board state
                  Shape: (num_channels, height, width) for Antiyoy: (22, 6, 6)

        Returns:
            pi: Probability distribution over actions (numpy array of size action_size)
                Higher values = network thinks this action is better
            v: Estimated value of this position (float in range [-1, 1])
               +1 = network thinks current player will win
               -1 = network thinks current player will lose
                0 = network thinks it's a draw
        """

        # ===================================================================
        # PREPARE INPUT
        # Convert numpy array to PyTorch tensor
        # ===================================================================
        board = torch.FloatTensor(board.astype(np.float64))

        # Move to GPU if available
        if args.cuda:
            board = board.contiguous().cuda()

        # Add batch dimension (network expects batches)
        board = board.view(1, self.num_channels, self.board_y, self.board_x)

        # ===================================================================
        # FORWARD PASS
        # Set to evaluation mode (disables dropout, batch norm uses running stats)
        # ===================================================================
        self.nnet.eval()

        # Disable gradient computation for faster inference
        with torch.no_grad():
            pi, v = self.nnet(board)

        # ===================================================================
        # PREPARE OUTPUT
        # Convert from log probabilities to probabilities
        # ===================================================================
        # Network outputs log probabilities (log_softmax)
        # We need to exponentiate to get actual probabilities
        pi = torch.exp(pi).data.cpu().numpy()[0]

        # Value is already in [-1, 1] range from tanh
        v = v.data.cpu().numpy()[0]

        return pi, v

    def loss_pi(self, targets, outputs):
        """
        Compute policy loss (cross-entropy).

        The policy loss measures how different the network's predicted
        action probabilities are from the MCTS-derived probabilities.

        This is cross-entropy loss:
        - Targets are the "ground truth" from MCTS
        - Outputs are the network's predictions (log probabilities)
        - Loss is high when network disagrees with MCTS
        - Loss is low when network matches MCTS

        Args:
            targets: MCTS policy (probability distribution)
            outputs: Network predictions (log probabilities)

        Returns:
            Average cross-entropy loss over the batch
        """
        # Cross-entropy: -sum(targets * log(outputs))
        # Since outputs are already log probabilities, we just multiply
        return -torch.sum(targets * outputs) / targets.size()[0]

    def loss_v(self, targets, outputs):
        """
        Compute value loss (mean squared error).

        The value loss measures how different the network's position
        evaluation is from the actual game outcome.

        This is mean squared error:
        - Targets are actual game outcomes (+1, 0, -1)
        - Outputs are network's predictions (also in [-1, 1])
        - Loss is high when network's evaluation is far from outcome
        - Loss is low when network correctly evaluates positions

        Args:
            targets: Actual game outcomes
            outputs: Network value predictions

        Returns:
            Average mean squared error over the batch
        """
        # MSE: mean((targets - outputs)^2)
        return torch.sum((targets - outputs.view(-1)) ** 2) / targets.size()[0]

    def save_checkpoint(self, folder='checkpoint', filename='checkpoint.pth.tar'):
        """
        Save model checkpoint to disk.

        This saves the network's weights so training can be resumed later.
        Checkpoints are saved after each iteration of self-play.

        Args:
            folder: Directory to save checkpoint in
            filename: Name of checkpoint file
        """
        filepath = os.path.join(folder, filename)

        # Create folder if it doesn't exist
        if not os.path.exists(folder):
            print(f"Checkpoint Directory does not exist! Making directory {folder}")
            os.makedirs(folder)
        else:
            print(f"Checkpoint Directory exists! Saving to {filepath}")

        # Save model state
        torch.save({
            'state_dict': self.nnet.state_dict(),
        }, filepath)

    def load_checkpoint(self, folder='checkpoint', filename='checkpoint.pth.tar'):
        """
        Load model checkpoint from disk.

        This restores the network's weights from a previous training run.

        Args:
            folder: Directory containing checkpoint
            filename: Name of checkpoint file
        """
        filepath = os.path.join(folder, filename)

        # Check if file exists
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"No model in path {filepath}")

        # Load checkpoint
        map_location = None if args.cuda else 'cpu'
        checkpoint = torch.load(filepath, map_location=map_location)

        # Restore network weights
        self.nnet.load_state_dict(checkpoint['state_dict'])

        print(f"Loaded checkpoint from {filepath}")


# ===================================================================
# TRAINING TIPS AND TUNING GUIDE
# ===================================================================
"""
How to improve training performance:

1. LEARNING RATE (lr):
   - Too high: Training unstable, loss oscillates
   - Too low: Training too slow
   - Symptom of too high: Loss explodes or oscillates wildly
   - Symptom of too low: Loss decreases very slowly
   - Fix: Try values like 0.01, 0.001, 0.0001

2. BATCH SIZE (batch_size):
   - Larger: More stable gradients, but uses more memory
   - Smaller: More frequent updates, but noisier gradients
   - Symptom of too large: Out of memory errors
   - Symptom of too small: Very noisy loss, unstable training
   - Fix: Increase until you run out of memory, then reduce slightly

3. NETWORK SIZE (num_channels, num_res_blocks):
   - Larger: More capacity, can learn complex patterns
   - Smaller: Faster training, but may underfit
   - Symptom of too large: Overfitting (training loss << validation loss)
   - Symptom of too small: Underfitting (high loss on both train and val)
   - Fix: Start small, increase if underfitting

4. DROPOUT (dropout):
   - Higher: More regularization, prevents overfitting
   - Lower: Less regularization, may overfit
   - Symptom of too high: Network can't learn (high training loss)
   - Symptom of too low: Overfitting (train loss << val loss)
   - Fix: Typical values are 0.2-0.4

5. EPOCHS (epochs):
   - More: Better convergence, but slower
   - Fewer: Faster iterations, but may not converge
   - Symptom of too few: Loss still decreasing at end of training
   - Symptom of too many: Loss plateaus, wastes time
   - Fix: Look at loss curves, stop when loss plateaus

6. MONITORING TRAINING:
   - Watch the loss values during training
   - Policy loss and value loss should both decrease
   - If losses oscillate: Reduce learning rate
   - If losses don't decrease: Increase learning rate or network size
   - If training loss << validation loss: Overfitting (increase dropout)
   - If both losses are high: Underfitting (increase network size)

7. GPU vs CPU:
   - GPU is ~10-100x faster for neural network training
   - If using CPU: Reduce batch_size and num_channels for speed
   - Check args.cuda to see if GPU is being used
"""
