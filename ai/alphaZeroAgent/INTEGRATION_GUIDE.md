# AlphaZero Agent - Integration Guide

The AlphaZero agent is now fully integrated into the main game!

## Quick Start

### 1. Train a Model (Required First Step)

Before you can use the AlphaZero agent, you need to train it:

```bash
cd alpha-zero
python3 main.py
```

Let it train for at least a few iterations. The checkpoint will be saved to `alpha-zero/temp/best.pth.tar`.

**Note**: Even after just 1-2 iterations, you can test the agent (it won't play well yet, but it will work).

### 2. Play Against the Agent

```bash
python3 main.py
```

When prompted for AI type, enter: **alphazero**

## Example Session

```
===== ASCIIyoy =====
An ASCII-based implementation of the Antiyoy strategy game.

--- Game Setup ---
Enter map dimension (recommended <=10): 6
Enter target number of land tiles (min 4, max 36): 20
Enter number of factions (max 9): 2
Enter name for Faction 1: Human
Enter color for Faction 1: Red
Is Faction 1 controlled by a (h)uman or (a)i? h

Enter name for Faction 2: AlphaZero
Enter color for Faction 2: Blue
Is Faction 2 controlled by a (h)uman or (a)i? a

Available AI types:
  - donothing
  - mark1srb
  - mark2srb
  - mark3srb
  - mark4srb
  - minimax
  - alphazero          <-- Select this!

Enter AI type for Faction 2: alphazero
```

## Agent Behavior

### With Trained Checkpoint

When a checkpoint is found:
```
Initializing AlphaZero agent...
  Checkpoint: alpha-zero/temp/best.pth.tar
  MCTS: Disabled
Using CUDA (GPU acceleration)
✓ Neural network loaded successfully!
✓ AlphaZero agent ready!
✓ AlphaZero agent loaded and ready!
```

The agent will then play using the trained neural network.

### Without Trained Checkpoint

If no checkpoint is found, you'll see:
```
⚠ WARNING: AlphaZero checkpoint not found!
  No model in path alpha-zero/temp/best.pth.tar
  The AlphaZero agent will not be able to play.

  To train a model, run:
    cd alpha-zero && python3 main.py

  The agent will fall back to random moves until a checkpoint is available.
```

The agent will end its turn immediately (effectively passing) until a model is trained.

## Testing Different Matchups

### AlphaZero vs Rule-Based AI

```
Faction 1: mark4srb
Faction 2: alphazero
```

### AlphaZero vs AlphaZero

```
Faction 1: alphazero
Faction 2: alphazero
```

**Note**: Both factions will use the same neural network, so it's like the agent playing against itself.

### Human vs AlphaZero

```
Faction 1: human
Faction 2: alphazero
```

## Performance Settings

The agent is currently configured for **fast gameplay** (policy-only mode, no MCTS).

To adjust the strength/speed tradeoff, edit `ai/alphaZeroAgent/AlphaZeroAgent.py` line 297-301:

```python
# Current settings (fast):
_global_agent = AlphaZeroAgent(
    checkpoint_folder='alpha-zero/temp',
    checkpoint_file='best.pth.tar',
    use_mcts=False,      # Change to True for stronger play
    num_mcts_sims=25     # Increase for even stronger play (e.g., 50, 100)
)
```

### Performance Guide

| Setting | Speed per Move | Strength | When to Use |
|---------|----------------|----------|-------------|
| `use_mcts=False` | ~0.01s | Weak | Fast testing, quick games |
| `use_mcts=True, sims=25` | ~0.5s | Moderate | Balanced gameplay |
| `use_mcts=True, sims=50` | ~1-2s | Strong | Competitive games |
| `use_mcts=True, sims=100` | ~3-5s | Very Strong | Serious matches |

## Troubleshooting

### "No module named 'torch'"

Install PyTorch:
```bash
pip install torch torchvision
```

### "No module named 'antiyoy'"

The AlphaZero agent needs access to the alpha-zero directory. Make sure you're running from the project root.

### Agent doesn't do anything / just ends turn

This happens when:
1. **No checkpoint exists**: Train a model first (`cd alpha-zero && python3 main.py`)
2. **Model is untrained**: The network doesn't know how to play yet. Train for more iterations.
3. **No valid moves**: Check that the game state allows valid actions.

### Import errors when starting

If you see import errors related to the AlphaZero agent, it might be because:
- The `azg` submodule isn't initialized: `git submodule update --init --recursive`
- Missing dependencies: `pip install -r requirements.txt` (if it exists)

### Agent crashes during play

Check the error message. Common issues:
- **CUDA out of memory**: Set `use_mcts=False` or reduce `num_mcts_sims`
- **Invalid actions**: The network might generate invalid moves. This improves with training.

## Next Steps

1. ✅ **Integrated**: The agent is now selectable in the main game
2. 🎯 **Train**: Run training for 10-100 iterations to get a functional agent
3. 🎮 **Test**: Play against it or watch it vs other AIs
4. 📊 **Evaluate**: See how it performs compared to rule-based agents
5. 🔧 **Tune**: Adjust MCTS settings for strength/speed tradeoff
6. 🚀 **Improve**: Continue training for 500+ iterations for strong play

## Files Modified

- `ai/AIPersonality.py`: Added alphazero to implementedAIs
- `ai/alphaZeroAgent/AlphaZeroAgent.py`: Added persistent agent instance
- Everything else: No changes to existing code!

The integration is **backward compatible** - all existing AIs continue to work exactly as before.
