# AlphaZero Agent

AI agent that uses a trained AlphaZero neural network to play Antiyoy.

## Features

- ✓ Implements standard `playTurn(scenario, faction)` interface
- ✓ Compatible with existing AI framework
- ✓ Supports both MCTS mode (strong, slow) and policy-only mode (fast, weaker)
- ✓ Loads trained checkpoints from `alpha-zero/temp/`
- ✓ Automatically converts between numpy arrays and game objects

## Usage

### Quick Start (Simple Function)

```python
from ai.alphaZeroAgent import playTurn

# Use in your game (creates agent on the fly)
actions = playTurn(scenario, faction)
```

**Note**: This creates a new agent each turn, which is inefficient. Better to create an agent instance once and reuse it.

### Recommended Usage (Reusable Agent)

```python
from ai.alphaZeroAgent import AlphaZeroAgent

# Create agent once at game start
agent = AlphaZeroAgent(
    checkpoint_folder='alpha-zero/temp',
    checkpoint_file='best.pth.tar',
    use_mcts=True,      # True for strong play, False for fast play
    num_mcts_sims=50    # More sims = stronger but slower
)

# Reuse agent for each turn
actions = agent.playTurn(scenario, faction)
```

### Configuration Options

```python
agent = AlphaZeroAgent(
    # Path to trained model
    checkpoint_folder='alpha-zero/temp',
    checkpoint_file='best.pth.tar',

    # Playing strength vs speed
    use_mcts=True,          # False = fast but weaker (policy only)
                            # True = slow but stronger (MCTS + policy)

    num_mcts_sims=50,       # MCTS simulations per move (if use_mcts=True)
                            # 25 = fast, 50 = balanced, 100+ = strong

    temperature=0           # 0 = greedy (always best move)
                            # >0 = stochastic (sample from distribution)
)
```

### Performance Trade-offs

| Mode | Speed (per move) | Strength | Use Case |
|------|------------------|----------|----------|
| Policy only (`use_mcts=False`) | ~0.01s | Weak | Quick testing, fast games |
| MCTS 25 sims | ~0.5s | Moderate | Balanced play |
| MCTS 50 sims | ~1-2s | Strong | Competitive games |
| MCTS 100+ sims | ~3-5s | Very strong | Tournament play |

## How It Works

1. **State Conversion**: Converts `Scenario` object → 23×6×6 numpy array
2. **Neural Network**: Predicts action probabilities and position value
3. **MCTS (optional)**: Searches game tree using neural network for evaluation
4. **Action Selection**: Chooses best action from policy
5. **Action Conversion**: Converts action index → `Action` objects
6. **Return**: Returns list of `(Action, province)` tuples

## Requirements

- Trained AlphaZero checkpoint (from `alpha-zero/main.py` training)
- PyTorch with CUDA support (recommended for speed)
- alpha-zero-general framework

## Troubleshooting

### "No model in path" error

Make sure you've trained a model first:
```bash
cd alpha-zero
python3 main.py  # Train for at least a few iterations
```

The checkpoint will be saved to `alpha-zero/temp/best.pth.tar`.

### Agent makes invalid moves

This can happen if:
- The model is not trained enough (try more iterations)
- There's a mismatch between training and game state
- The action masking isn't working properly

Check that valid moves are being masked correctly.

### Slow performance

If MCTS is too slow:
- Reduce `num_mcts_sims` (try 25 or lower)
- Use `use_mcts=False` for policy-only mode (much faster)
- Make sure GPU is being used (check CUDA availability)

### Agent always ends turn immediately

This usually means:
- No valid actions are available
- The model hasn't learned to recognize valid moves yet
- Need more training iterations

## Integration Example

```python
# In your main game loop
from ai.alphaZeroAgent import AlphaZeroAgent

# Initialize agents
agent_p1 = AlphaZeroAgent(use_mcts=True, num_mcts_sims=50)
agent_p2 = AlphaZeroAgent(use_mcts=True, num_mcts_sims=50)

# Game loop
while not game_over:
    current_faction = scenario.factions[scenario.indexOfFactionToPlay]

    if current_faction == faction1:
        actions = agent_p1.playTurn(scenario, current_faction)
    else:
        actions = agent_p2.playTurn(scenario, current_faction)

    # Apply actions
    for action, province in actions:
        scenario.applyAction(action, province)

    # Advance turn
    scenario.advanceTurn()
```

## Next Steps

After training a model:

1. **Test the agent**: Create simple games to see if it plays reasonably
2. **Evaluate strength**: Pit it against rule-based agents
3. **Tune MCTS**: Experiment with different simulation counts
4. **Continue training**: More iterations = stronger play

## Files

- `AlphaZeroAgent.py`: Main agent implementation
- `__init__.py`: Package initialization
- `README.md`: This file
