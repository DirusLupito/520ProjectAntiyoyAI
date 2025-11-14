# Antiyoy Alpha-Zero-General Integration

This directory contains the integration of the Antiyoy game with the [alpha-zero-general](https://github.com/suragnair/alpha-zero-general) framework for training neural network agents.

## Overview

The implementation provides a bridge between Antiyoy's Python object-based game state and alpha-zero-general's numpy array-based interface. Key features:

- **6×6 hexagonal board**: Smaller board for faster training
- **2-player support**: Required by alpha-zero-general
- **Multi-action turns**: Players can perform multiple actions before ending turn
- **Full game rules**: All units (soldiers tiers 1-4, capital, farm, towers), structures, trees, and resource economy
- **Single province per faction**: Simplified to avoid complex province splitting/merging

## File Structure

```
alpha-zero/
├── README.md                    # This file
└── antiyoy/
    ├── __init__.py              # Package initialization
    ├── AntiyoyGame.py          # Game interface implementation
    ├── AntiyoyLogic.py         # Board logic and encoding/decoding
    └── test_antiyoy.py         # Basic tests
```

## Installation

1. Ensure you have the alpha-zero-general library available (in the `azg/` directory)
2. Install required dependencies:
   ```bash
   pip install numpy
   ```

## Usage

### Basic Game Interface

```python
from antiyoy.AntiyoyGame import AntiyoyGame

# Create game
game = AntiyoyGame()

# Get initial board
board = game.getInitBoard()

# Get valid moves for current player
player = 1
valid_moves = game.getValidMoves(board, player)

# Apply an action
action = 972  # Example: end turn action
next_board, next_player = game.getNextState(board, player, action)

# Check if game ended
result = game.getGameEnded(next_board, next_player)
# Returns: 0 (ongoing), 1 (win), -1 (loss), 1e-4 (draw)
```

### Testing

Run the basic tests:

```bash
python3 alpha-zero/antiyoy/test_antiyoy.py
```

This will test:
- Game initialization
- Board encoding/decoding
- Valid move generation
- Playing random moves
- Canonical form transformation

## Implementation Details

### State Encoding (22 channels, 6×6 grid)

The board state is encoded as a 22-channel numpy array:

| Channels | Description |
|----------|-------------|
| 0-1 | Tile ownership (Player 1, Player 2) |
| 2 | Water tiles |
| 3-6 | Player 1 soldiers (tiers 1-4) |
| 7-10 | Player 2 soldiers (tiers 1-4) |
| 11-14 | Structures (capital, farm, tower1, tower2) |
| 15-16 | Trees and gravestones |
| 17 | Soldier movement status |
| 18-19 | Province resources (normalized) |
| 20-21 | Province income (normalized) |

### Action Encoding (~973 actions)

Actions are encoded as integers:

1. **Move actions** (0-719): `tile_index × 20 + destination_offset`
   - 36 tiles × 20 max destinations per tile = 720 actions

2. **Build actions** (720-971): `720 + tile_index × 7 + unit_type_index`
   - 36 tiles × 7 unit types = 252 actions
   - Unit types: soldierTier1-4, farm, tower1, tower2

3. **End turn action** (972): Last action index

### Multi-Action Turns

Unlike traditional board games, Antiyoy allows multiple actions per turn. Implementation:

- Each call to `getNextState()` processes ONE action
- If action is **move/build**: same player continues (next_player = player)
- If action is **end turn**: switch players (next_player = -player)
- This allows MCTS to plan sequences of actions

### Key Design Decisions

1. **Single province per faction**: Simplifies state representation
2. **Full game rules**: All units and mechanics included
3. **6×6 board**: Balance between complexity and training speed
4. **No symmetries (yet)**: Hex grid symmetries are complex; may add later
5. **Normalized resources**: Resources and income scaled to [0, 1] range

## Integration with Alpha-Zero-General

To use with alpha-zero-general:

1. Import the game:
   ```python
   from antiyoy import Game as AntiyoyGame
   ```

2. The game implements the required `Game` interface:
   - `getInitBoard()`
   - `getBoardSize()`
   - `getActionSize()`
   - `getNextState(board, player, action)`
   - `getValidMoves(board, player)`
   - `getGameEnded(board, player)`
   - `getCanonicalForm(board, player)`
   - `getSymmetries(board, pi)`
   - `stringRepresentation(board)`

3. Use with alpha-zero-general's training infrastructure:
   ```python
   from Coach import Coach
   from antiyoy import Game as AntiyoyGame

   game = AntiyoyGame()
   # ... configure neural network and training ...
   coach = Coach(game, nnet, args)
   coach.learn()
   ```

## Known Limitations

1. **Encoding/decoding precision**: Small loss of precision in resource values due to normalization
2. **Province reconstruction**: Reconstructed scenarios have simplified province structure (one per faction)
3. **Random starting positions**: Each game starts with a random map layout
4. **Large action space**: ~973 actions (most masked as invalid at any state)
5. **No symmetries**: Hex grid symmetries not yet implemented

## Future Improvements

- [ ] Implement hex grid symmetries for data augmentation
- [ ] Add support for fixed starting positions
- [ ] Optimize action space encoding
- [ ] Add neural network architecture (AntiyoyNNet.py)
- [ ] Create training scripts and configurations
- [ ] Add evaluation and pit scripts
- [ ] Implement checkpointing and model persistence

## Testing

The implementation has been tested with:
- ✓ Basic game initialization
- ✓ State encoding/decoding (with minor precision loss)
- ✓ Valid move generation
- ✓ Random gameplay
- ✓ Canonical form transformation
- ✓ String representation for hashing

## References

- [Alpha-Zero-General](https://github.com/suragnair/alpha-zero-general) - The framework this integrates with
- [Antiyoy](https://yiotro.itch.io/antiyoy) - Original game inspiration
- [AlphaZero Paper](https://arxiv.org/abs/1712.01815) - Original AlphaZero research

## License

This integration follows the same license as the parent project.
