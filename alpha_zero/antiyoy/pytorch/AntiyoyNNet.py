"""
AntiyoyNNet.py - Neural Network Architecture for Antiyoy

This module defines the neural network architecture for the Antiyoy game.
The network takes a 22-channel 5x5 board representation as input and outputs:
- Policy head: Probability distribution over 973 possible actions
- Value head: Estimated value of the current position (-1 to 1)

Architecture Design Principles:
1. Input Processing: Multiple convolutional layers to extract spatial features
2. Feature Extraction: Residual blocks for deeper feature learning
3. Two-headed output: Separate policy and value predictions

The architecture is inspired by AlphaZero but scaled for the Antiyoy game's
complexity and board size.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from azg.utils import dotdict


class ResidualBlock(nn.Module):
    """
    Residual Block with skip connections.

    Residual blocks help with gradient flow in deep networks and allow
    the network to learn more complex features. The skip connection allows
    gradients to flow directly through the block.

    Architecture:
        Input -> Conv2d -> BatchNorm -> ReLU -> Conv2d -> BatchNorm -> Add(Input) -> ReLU -> Output

    This is the core building block of modern deep neural networks for board games.
    """

    def __init__(self, num_channels):
        """
        Args:
            num_channels: Number of input/output channels (same for both)
        """
        super(ResidualBlock, self).__init__()

        # First convolutional layer
        # 3x3 kernel with padding=1 maintains spatial dimensions
        self.conv1 = nn.Conv2d(num_channels, num_channels, 3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(num_channels)

        # Second convolutional layer
        self.conv2 = nn.Conv2d(num_channels, num_channels, 3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(num_channels)

    def forward(self, x):
        """
        Forward pass through the residual block.

        Args:
            x: Input tensor of shape (batch_size, num_channels, height, width)

        Returns:
            Output tensor of same shape as input
        """
        # Save input for skip connection
        residual = x

        # First conv block
        out = self.conv1(x)
        out = self.bn1(out)
        out = F.relu(out)

        # Second conv block (no ReLU yet)
        out = self.conv2(out)
        out = self.bn2(out)

        # Add skip connection
        out += residual

        # Final ReLU activation
        out = F.relu(out)

        return out


class AntiyoyNNet(nn.Module):
    """
    Neural Network for Antiyoy game.

    This network processes the 22-channel board state and outputs both
    a policy (which action to take) and a value (how good is this position).

    Architecture Overview:
    1. Input Layer: Processes 22-channel 5x5 board
    2. Initial Convolution: Expands to num_channels features
    3. Residual Blocks: Deep feature extraction
    4. Policy Head: Outputs probability distribution over actions
    5. Value Head: Outputs position evaluation

    Key Hyperparameters (can be tuned for better performance):
    - num_channels: Width of the network (more = more capacity but slower)
    - num_res_blocks: Depth of the network (more = can learn more complex patterns)
    - dropout: Regularization to prevent overfitting
    """

    def __init__(self, game, args):
        """
        Initialize the neural network.

        Args:
            game: AntiyoyGame instance (used to get board size and action size)
            args: dotdict containing hyperparameters:
                - num_channels: Number of convolutional filters (default: 256)
                - num_res_blocks: Number of residual blocks (default: 5)
                - dropout: Dropout rate for regularization (default: 0.3)
        """
        super(AntiyoyNNet, self).__init__()

        # Extract game parameters
        # board_x, board_y are actually (num_channels, height, width) for Antiyoy
        # So board_x = 22 (channels), board_y = 5 (height), board_z = 5 (width)
        board_dims = game.getBoardSize()
        if len(board_dims) == 3:
            self.num_input_channels, self.board_y, self.board_x = board_dims
        else:
            # Fallback for 2D boards
            self.board_x, self.board_y = board_dims
            self.num_input_channels = 1

        self.action_size = game.getActionSize()
        self.args = args

        # Network hyperparameters
        self.num_channels = args.num_channels  # Width of the network
        self.num_res_blocks = args.num_res_blocks  # Depth of the network

        # ===================================================================
        # INITIAL CONVOLUTION BLOCK
        # Expands the 22-channel input to num_channels for feature extraction
        # ===================================================================
        self.conv_input = nn.Conv2d(
            self.num_input_channels,  # 22 input channels (our board encoding)
            self.num_channels,         # Expand to num_channels features
            3,                         # 3x3 kernel
            stride=1,
            padding=1                  # Padding maintains spatial dimensions
        )
        self.bn_input = nn.BatchNorm2d(self.num_channels)

        # ===================================================================
        # RESIDUAL BLOCKS
        # Stack of residual blocks for deep feature extraction
        # More blocks = can learn more complex patterns
        # Typical values: 5-20 blocks
        # ===================================================================
        self.res_blocks = nn.ModuleList([
            ResidualBlock(self.num_channels)
            for _ in range(self.num_res_blocks)
        ])

        # ===================================================================
        # POLICY HEAD
        # Predicts probability distribution over all possible actions
        # Output size: action_size (973 for Antiyoy)
        # ===================================================================

        # Reduce channels before fully connected layers
        self.policy_conv = nn.Conv2d(self.num_channels, 32, 1)  # 1x1 conv to reduce channels
        self.policy_bn = nn.BatchNorm2d(32)

        # Calculate flattened size after policy_conv
        # Shape: (batch, 32, board_y, board_x)
        policy_flat_size = 32 * self.board_y * self.board_x

        # Fully connected layers for policy
        self.policy_fc1 = nn.Linear(policy_flat_size, 512)
        self.policy_fc2 = nn.Linear(512, self.action_size)

        # ===================================================================
        # VALUE HEAD
        # Predicts the value of the current position
        # Output: Single value in range [-1, 1]
        # -1 = certain loss, 0 = draw, +1 = certain win
        # ===================================================================

        # Reduce channels before fully connected layers
        self.value_conv = nn.Conv2d(self.num_channels, 16, 1)  # 1x1 conv
        self.value_bn = nn.BatchNorm2d(16)

        # Calculate flattened size
        value_flat_size = 16 * self.board_y * self.board_x

        # Fully connected layers for value
        self.value_fc1 = nn.Linear(value_flat_size, 256)
        self.value_fc2 = nn.Linear(256, 1)  # Single value output

    def forward(self, s):
        """
        Forward pass through the network.

        Args:
            s: Input tensor of shape (batch_size, num_input_channels, board_y, board_x)
               For Antiyoy: (batch_size, 22, 5, 5)

        Returns:
            pi: Log probabilities for actions, shape (batch_size, action_size)
                Use with log_softmax for numerical stability
            v: Predicted value, shape (batch_size, 1)
               Values in range [-1, 1] via tanh activation
        """

        # ===================================================================
        # INPUT PROCESSING
        # ===================================================================
        # Reshape if needed (handle different input formats)
        # Expected shape: (batch_size, num_input_channels, board_y, board_x)
        if len(s.shape) == 3:
            # Add batch dimension if missing
            s = s.unsqueeze(0)

        # ===================================================================
        # INITIAL CONVOLUTION
        # Expand input channels to num_channels for feature extraction
        # ===================================================================
        x = self.conv_input(s)
        x = self.bn_input(x)
        x = F.relu(x)

        # ===================================================================
        # RESIDUAL BLOCKS
        # Deep feature extraction with skip connections
        # Each block learns to refine the features from previous blocks
        # ===================================================================
        for res_block in self.res_blocks:
            x = res_block(x)

        # At this point, x has shape: (batch_size, num_channels, board_y, board_x)
        # It contains rich spatial features extracted from the board

        # ===================================================================
        # POLICY HEAD
        # Transform features into action probabilities
        # ===================================================================
        pi = self.policy_conv(x)
        pi = self.policy_bn(pi)
        pi = F.relu(pi)

        # Flatten for fully connected layers
        pi = pi.view(pi.size(0), -1)  # (batch_size, 32 * board_y * board_x)

        # Fully connected layers with dropout for regularization
        pi = F.dropout(
            F.relu(self.policy_fc1(pi)),
            p=self.args.dropout,
            training=self.training  # Only apply dropout during training
        )
        pi = self.policy_fc2(pi)  # (batch_size, action_size)

        # Apply temperature scaling to sharpen the policy distribution
        # Lower temperature (< 1.0) makes the policy more confident/spiky
        # Higher temperature (> 1.0) makes the policy more uniform
        # Temperature of 0.5-0.7 often works well for increasing volatility
        temperature = 0.6  # Adjust this value: lower = more volatile
        pi = pi / temperature

        # Apply log_softmax for numerical stability
        # This is preferred over softmax + log for numerical reasons
        pi = F.log_softmax(pi, dim=1)

        # ===================================================================
        # VALUE HEAD
        # Transform features into position evaluation
        # ===================================================================
        v = self.value_conv(x)
        v = self.value_bn(v)
        v = F.relu(v)

        # Flatten for fully connected layers
        v = v.view(v.size(0), -1)  # (batch_size, 16 * board_y * board_x)

        # Fully connected layers with dropout
        v = F.dropout(
            F.relu(self.value_fc1(v)),
            p=self.args.dropout,
            training=self.training
        )
        v = self.value_fc2(v)  # (batch_size, 1)

        # Apply tanh to bound output to [-1, 1]
        # -1 = loss, 0 = draw, +1 = win
        v = torch.tanh(v)

        return pi, v


# ===================================================================
# ARCHITECTURE TUNING NOTES
# ===================================================================
"""
This neural network can be tuned in several ways for better performance:

1. NETWORK WIDTH (num_channels):
   - Default: 256
   - Smaller (128): Faster training, less capacity, may underfit
   - Larger (512): Slower training, more capacity, may overfit
   - Typical range: 128-512
   - Impact: Affects how many features can be learned at each layer

2. NETWORK DEPTH (num_res_blocks):
   - Default: 5
   - Fewer (2-3): Faster, shallower features, good for simple games
   - More (10-20): Slower, deeper features, good for complex games
   - Typical range: 3-15
   - Impact: Affects how complex patterns the network can recognize

3. DROPOUT RATE:
   - Default: 0.3
   - Lower (0.1): Less regularization, may overfit
   - Higher (0.5): More regularization, may underfit
   - Typical range: 0.2-0.4
   - Impact: Prevents overfitting to training data

4. POLICY/VALUE HEAD SIZE:
   - Current: 512 -> action_size (policy), 256 -> 1 (value)
   - Can increase for more capacity: 1024 -> action_size
   - Can decrease for faster training: 256 -> action_size
   - Impact: Affects final prediction quality

5. ALTERNATIVE ARCHITECTURES:
   - Add more convolutional layers in policy/value heads
   - Use different activation functions (LeakyReLU, ELU)
   - Add attention mechanisms for focusing on important board regions
   - Use different residual block designs (bottleneck, preactivation)

For Antiyoy specifically:
- Start with num_channels=256, num_res_blocks=5
- If underfitting: Increase width or depth
- If overfitting: Increase dropout or decrease capacity
- If too slow: Reduce width or depth
- Monitor training loss, validation performance, and playing strength
"""
