# Antiyoy AI - Setup Guide

## Project Structure

The project follows standard Python packaging conventions:

```
520ProjectAntiyoyAI/
├── ai/                    # AI agent implementations
├── game/                  # Core game logic
├── rl/                    # Reinforcement learning code
├── tournaments/           # Tournament runner
├── azg/                   # Alpha-Zero-General framework
├── alpha_zero/            # AlphaZero training (proper Python package)
│   ├── main.py            # Training entry point
│   ├── run_training.py    # Auto-restart training wrapper
│   ├── Coach.py           # Self-play coach
│   ├── MCTS.py            # Monte Carlo Tree Search
│   ├── Arena.py           # Model evaluation
│   └── antiyoy/           # Antiyoy-specific implementations
│       ├── AntiyoyGame.py
│       ├── AntiyoyLogic.py
│       └── pytorch/       # Neural network models
├── setup.py               # Package configuration
├── requirements.txt       # Python dependencies
└── install.sh             # Installation script
```

## Quick Start

### 1. Run the Installation Script

```bash
./install.sh
```

This will:
- Create a virtual environment in `.venv/`
- Install the project package in development mode
- Install all dependencies from `requirements.txt`

### 2. Activate the Virtual Environment

```bash
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt.

### 3. Run AlphaZero Training

**Using Python module syntax (recommended):**
```bash
python -m alpha_zero.main
```

**With auto-restart on crashes:**
```bash
python -m alpha_zero.run_training
```

**Or run directly:**
```bash
python alpha_zero/main.py
python alpha_zero/run_training.py
```

## Import System

All packages follow standard Python import conventions:

```python
# Import from top-level packages
from game.Scenario import Scenario
from azg.utils import dotdict
from ai.AIPersonality import AIPersonality

# Import from alpha_zero package
from alpha_zero.Coach import Coach
from alpha_zero.antiyoy.AntiyoyGame import AntiyoyGame
from alpha_zero.MCTS import MCTS
```

**No path hacks, no workarounds - just clean Python!** ✨

## Key Changes Made

1. **Renamed `alpha-zero` → `alpha_zero`**: Follows Python naming conventions (no hyphens)
2. **Updated setup.py**: Includes all packages properly
3. **Added __init__.py files**: Created for all package directories
4. **Clean imports**: All imports use standard Python module paths
5. **Removed path hacks**: No `sys.path.append()` or manual path manipulation

## Running Tests

### Test Base Imports
```bash
source .venv/bin/activate
python3 -c "
from game.Scenario import Scenario
from azg.utils import dotdict
print('✓ Imports working!')
"
```

### Test Alpha-Zero Imports
```bash
python3 -c "
from alpha_zero.Coach import Coach
from alpha_zero.antiyoy.AntiyoyGame import AntiyoyGame
print('✓ Alpha-Zero imports working!')
"
```

## Troubleshooting

### ImportError: No module named 'X'

Make sure you:
1. Activated the virtual environment: `source .venv/bin/activate`
2. Installed the package: `pip install -e .`
3. Installed dependencies: `pip install -r requirements.txt`

### Module changes not reflected

If you edit the code and changes aren't showing up:
```bash
# Reinstall in development mode
pip install -e . --force-reinstall --no-deps
```

## Development Mode

The package is installed in "development mode" (`pip install -e .`), which means:
- Changes to Python files are immediately reflected (no reinstall needed)
- The package uses files in your working directory (not copies in site-packages)
- You can edit and run without reinstalling

## Deactivating the Virtual Environment

When you're done:
```bash
deactivate
```

## IDE Configuration

### VSCode

If using VSCode, select the Python interpreter:
1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Python: Select Interpreter"
3. Choose `.venv/bin/python`

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Click the gear icon → Add
3. Select "Existing environment"
4. Browse to `.venv/bin/python`

## Next Steps

Now that your environment is set up:

1. **Review training parameters**: See [POLICY_VOLATILITY_CHANGES.md](POLICY_VOLATILITY_CHANGES.md) for recent improvements
2. **Start training**: Run `python -m alpha_zero.run_training`
3. **Monitor progress**: Check `alpha_zero/temp/` for checkpoints and logs

## Package Dependencies

Key dependencies (from requirements.txt):
- **PyTorch 2.9.1**: Deep learning framework
- **NumPy 2.2.6**: Numerical computing
- **tqdm 4.67.1**: Progress bars
- **coloredlogs 15.0.1**: Colored logging output
- **dotdict 0.1**: Dictionary with dot notation access

All CUDA libraries are included for GPU acceleration if available.

## Alternative: Manual Setup

If you prefer to set up manually:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install package in development mode
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

## Running from Any Directory

Since everything uses proper Python modules, you can run from anywhere:

```bash
# From project root
python -m alpha_zero.main

# From a subdirectory
cd some/other/directory
python -m alpha_zero.main  # Still works!

# With full path
python /full/path/to/alpha_zero/main.py
```

All methods work correctly! 🎉
