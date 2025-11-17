"""
main.py - Training Script for Antiyoy Alpha-Zero Agent

This is the main entry point for training an Antiyoy agent using AlphaZero.

The training process works as follows:
1. Initialize the game and neural network
2. For each iteration:
   a. Play games of self-play using MCTS + current neural network
   b. Collect training examples (board positions, MCTS policies, outcomes)
   c. Train neural network on these examples
   d. Evaluate new network against old network
   e. Keep new network if it's better, otherwise keep old network
3. Repeat until the agent is strong enough

This process is based on the AlphaZero paper:
https://arxiv.org/abs/1712.01815
"""

import sys
import os
import logging

# Add alpha-zero directory to path so we can import setup_path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import setup_path  # Sets up paths for imports

import coloredlogs
from Coach import Coach
from antiyoy.AntiyoyGame import AntiyoyGame as Game
from antiyoy.pytorch.NNet import NNetWrapper as nn
from azg.utils import dotdict

# Set up logging
log = logging.getLogger(__name__)
coloredlogs.install(level='INFO')  # Change to DEBUG for more detailed output


# ===================================================================
# TRAINING HYPERPARAMETERS
# These control the training process and can be tuned for better results
# ===================================================================
args = dotdict({
    # ===================================================================
    # SELF-PLAY PARAMETERS
    # These control how games are played to generate training data
    # ===================================================================

    # Number of training iterations
    # Each iteration consists of: self-play -> train network -> evaluate
    # More iterations = longer training but better final performance
    # Typical range: 100-1000
    'numIters': 1000,

    # Number of self-play games per iteration
    # More games = more diverse training data but slower iterations
    # Fewer games = faster iterations but less diverse data
    # Typical range: 50-200
    'numEps': 50,

    # Temperature threshold for move selection
    # First N moves use temperature=1 (exploration)
    # After N moves use temperature=0 (exploitation/greedy)
    # Higher = more exploration in opening
    # Typical range: 10-20
    'tempThreshold': 15,

    # Number of MCTS simulations per move
    # More simulations = better move quality but slower
    # This is the key parameter for playing strength
    # Typical range: 25-800 (AlphaZero used 800)
    # Start with lower values (25-100) for faster training
    # INCREASED FOR MORE CONFIDENT POLICIES: 50-100 gives much better training signal
    'numMCTSSims': 100, # THIS IS CPU BOUND (probably what slows us down)

    # CPUCT parameter for MCTS exploration
    # Higher = more exploration of uncertain moves
    # Lower = more exploitation of known good moves
    # Typical range: 0.5-2.0
    'cpuct': 1.0,

    # Dirichlet noise parameters for root node exploration (AlphaZero technique)
    # Alpha controls the concentration of the Dirichlet distribution
    # Lower alpha = more concentrated noise = more diverse exploration
    # Typical range: 0.03 (chess) to 0.3 (Go) to 0.5 (many valid moves)
    'dirichletAlpha': 0.3,

    # Fraction of root policy that comes from Dirichlet noise
    # (1-epsilon)*policy + epsilon*noise
    # Higher = more exploration during self-play
    # Typical value: 0.25 (25% noise, 75% policy)
    'explorationFraction': 0.25,

    # Heuristic evaluation weight for max depth positions
    # When MCTS reaches max depth (1000), use heuristic evaluation instead of draw
    # This value scales the heuristic to indicate less certainty than true terminals
    # 0.5 = heuristic evaluations weighted at 50% of true terminal states
    # 1.0 = treat heuristic evaluations as confidently as true terminals
    # Typical range: 0.3-0.7
    'heuristic_weight': 0.5,

    # ===================================================================
    # EVALUATION PARAMETERS
    # These control how we decide if a new network is better
    # ===================================================================

    # Win threshold for accepting new network
    # New network must win this fraction of arena games to be accepted
    # Higher = more conservative (only accept clearly better networks)
    # Lower = more aggressive (accept marginally better networks)
    # Typical range: 0.55-0.60
    'updateThreshold': 0.51,

    # Number of games to play in arena for evaluation
    # More games = more reliable evaluation but slower
    # Fewer games = faster but less reliable
    # Typical range: 20-100
    'arenaCompare': 25,

    # ===================================================================
    # TRAINING DATA PARAMETERS
    # These control the training dataset
    # ===================================================================

    # Maximum number of training examples to keep in memory
    # Larger = more diverse data but uses more RAM
    # Smaller = less RAM usage but less diverse data
    # Should be larger than numEps * avg_game_length * numItersForTrainExamplesHistory
    'maxlenOfQueue': 200000,

    # Number of iterations of training examples to keep
    # We keep examples from the last N iterations
    # This creates a "window" of recent experience
    # Typical range: 10-30
    'numItersForTrainExamplesHistory': 20,

    # ===================================================================
    # CHECKPOINT PARAMETERS
    # These control saving and loading of models
    # ===================================================================

    # Directory to save checkpoints
    'checkpoint': './temp/',

    # Whether to load a previous model
    # Set to True to resume training from a checkpoint
    'load_model': True,

    # Checkpoint to load (if load_model is True)
    # Format: (folder, filename)
    'load_folder_file': ('./temp/', 'best.pth.tar'),
})


def main():
    """
    Main training loop.

    This function:
    1. Initializes the game and neural network
    2. Optionally loads a checkpoint
    3. Starts the learning process via Coach

    The Coach handles all the details of self-play, training, and evaluation.
    """

    # ===================================================================
    # INITIALIZATION
    # ===================================================================
    log.info('=' * 60)
    log.info('ANTIYOY ALPHAZERO TRAINING')
    log.info('=' * 60)

    # Initialize the game
    log.info('Loading %s...', Game.__name__)
    g = Game()

    log.info('Game Configuration:')
    log.info('  Board size: %s', g.getBoardSize())
    log.info('  Action size: %s', g.getActionSize())

    # Initialize the neural network
    log.info('Loading %s...', nn.__name__)
    nnet = nn(g)

    log.info('Neural Network Configuration:')
    log.info('  Input channels: 22 (board state encoding)')
    log.info('  Output size: %d (possible actions)', g.getActionSize())

    # ===================================================================
    # LOAD CHECKPOINT (if requested)
    # ===================================================================
    if args.load_model:
        checkpoint_path = os.path.join(args.load_folder_file[0], args.load_folder_file[1])
        if os.path.exists(checkpoint_path):
            log.info('Loading checkpoint "%s/%s"...',
                     args.load_folder_file[0], args.load_folder_file[1])
            nnet.load_checkpoint(args.load_folder_file[0], args.load_folder_file[1])
            log.info('Checkpoint loaded successfully!')
        else:
            log.warning('Checkpoint "%s" not found!', checkpoint_path)
            log.warning('Starting from scratch instead.')
            args.load_model = False  # Disable loading for training examples too
    else:
        log.warning('Not loading a checkpoint - starting from scratch!')
        log.warning('Training from scratch will take a long time.')
        log.warning('Consider setting load_model=True to resume from a checkpoint.')

    # ===================================================================
    # INITIALIZE COACH
    # The Coach manages the entire training process
    # ===================================================================
    log.info('Loading the Coach...')
    c = Coach(g, nnet, args)

    # Load previous training examples if resuming
    if args.load_model:
        log.info("Loading 'trainExamples' from file...")
        c.loadTrainExamples()
        log.info("Previous training examples loaded successfully!")

    # ===================================================================
    # START TRAINING
    # ===================================================================
    log.info('=' * 60)
    log.info('Starting the learning process 🎉')
    log.info('=' * 60)
    log.info('')
    log.info('Training Configuration:')
    log.info('  Iterations: %d', args.numIters)
    log.info('  Self-play games per iteration: %d', args.numEps)
    log.info('  MCTS simulations per move: %d', args.numMCTSSims)
    log.info('  Arena games for evaluation: %d', args.arenaCompare)
    log.info('  Update threshold: %.2f', args.updateThreshold)
    log.info('')
    log.info('This will take a long time. You can:')
    log.info('  - Monitor progress in the terminal')
    log.info('  - Checkpoints are saved to: %s', args.checkpoint)
    log.info('  - Press Ctrl+C to stop (progress is saved)')
    log.info('')
    log.info('=' * 60)

    # Start the learning loop
    # This will run until numIters is reached or user stops it
    c.learn()

    log.info('=' * 60)
    log.info('Training complete!')
    log.info('=' * 60)


if __name__ == "__main__":
    """
    Entry point when running this script directly.
    """
    main()


# ===================================================================
# USAGE GUIDE
# ===================================================================
"""
How to use this training script:

1. BASIC USAGE:
   python alpha-zero/main.py

   This will start training from scratch with default parameters.

2. RESUME FROM CHECKPOINT:
   Set 'load_model': True in args above
   Specify the checkpoint path in 'load_folder_file'

   Then run:
   python alpha-zero/main.py

3. ADJUST TRAINING SPEED:
   For faster iterations (for testing):
   - Reduce numEps (e.g., 10-20 games per iteration)
   - Reduce numMCTSSims (e.g., 25 simulations per move)
   - Reduce arenaCompare (e.g., 10-20 games)

   For better final performance:
   - Increase numEps (e.g., 200-400 games per iteration)
   - Increase numMCTSSims (e.g., 100-400 simulations per move)
   - Increase arenaCompare (e.g., 100 games)

4. MONITOR TRAINING:
   - Watch the terminal output for:
     * Self-play progress
     * Training loss (should decrease over time)
     * Arena results (new network vs old network)

   - Check checkpoints in the temp/ directory
   - You can interrupt training with Ctrl+C (progress is saved)

5. EVALUATE TRAINED MODEL:
   After training, you can:
   - Use the model to play against other agents
   - Visualize the policy and value predictions
   - Test on specific board positions

   See azg/pit.py for examples of model evaluation

6. COMMON ISSUES:

   Issue: Out of memory
   Solution: Reduce batch_size in antiyoy/pytorch/NNet.py

   Issue: Training too slow
   Solution: Reduce numMCTSSims or numEps, or use GPU

   Issue: Network not improving
   Solution: Increase numMCTSSims, or adjust neural network size

   Issue: Arena results show no improvement
   Solution: Reduce updateThreshold, or train for more iterations

7. EXPECTED TIMELINE:
   - Iteration 0-10: Random play, network learns basic rules
   - Iteration 10-50: Network learns simple tactics
   - Iteration 50-200: Network learns strategy
   - Iteration 200+: Network refines advanced play

   Full training to strong play: 500-1000 iterations
   With default settings: ~10-50 hours depending on hardware

8. HARDWARE RECOMMENDATIONS:
   - CPU: Expect ~5-30 seconds per move during self-play
   - GPU: Expect ~1-5 seconds per move during self-play
   - RAM: ~8-16 GB recommended
   - Disk: ~1-10 GB for checkpoints

   GPU strongly recommended for serious training!

9. TUNING FOR YOUR SYSTEM:
   If you have limited resources:
   - Set numMCTSSims to 25-50
   - Set numEps to 50
   - Set arenaCompare to 20
   - Reduce num_channels in pytorch/NNet.py to 128

   If you have powerful hardware:
   - Set numMCTSSims to 200-400
   - Set numEps to 200
   - Set arenaCompare to 100
   - Increase num_channels in pytorch/NNet.py to 512

10. INTERPRETING RESULTS:
    During training, you'll see output like:

    "Arena.playGames (1): 0.550"
    - This means the new network won 55% of games against old network
    - If > updateThreshold (0.55), new network is accepted
    - If < updateThreshold, old network is kept

    "PITTING NEW NET AGAINST OLD NET"
    - This is the evaluation phase
    - Best of 3 types of matchups:
      * New as player 1
      * New as player 2
    - Ensures network isn't biased to one player
"""
