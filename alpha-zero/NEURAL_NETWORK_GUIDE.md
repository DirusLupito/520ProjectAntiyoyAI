# Antiyoy Neural Network Architecture Guide

## Overview

The neural network for Antiyoy is designed following AlphaZero principles with architecture tailored to the game's complexity. This guide explains the architecture, how to modify it, and how to train effectively.

## Architecture Summary

### Network Structure

```
Input (22, 6, 6) - 22-channel 6x6 board state
    ↓
Initial Convolution (256 filters, 3x3) + BatchNorm + ReLU
    ↓
Residual Block 1 (256 filters)
Residual Block 2 (256 filters)
Residual Block 3 (256 filters)
Residual Block 4 (256 filters)
Residual Block 5 (256 filters)
    ↓
   / \
  /   \
 ↓     ↓
Policy Head    Value Head
     ↓             ↓
  (973,)          (1,)
```

### Key Components

#### 1. **Input Processing** ([AntiyoyNNet.py:97-107](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py#L97-L107))
- **Input**: 22×6×6 tensor (22 channels encoding board state)
- **Initial Conv**: Expands to 256 feature channels
- **Purpose**: Transform raw board encoding into rich feature representation

#### 2. **Residual Blocks** ([AntiyoyNNet.py:27-74](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py#L27-L74))
- **Structure**: Conv → BatchNorm → ReLU → Conv → BatchNorm → Add Skip → ReLU
- **Count**: 5 blocks (configurable)
- **Purpose**: Deep feature extraction with gradient flow
- **Key Feature**: Skip connections prevent vanishing gradients

#### 3. **Policy Head** ([AntiyoyNNet.py:109-126](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py#L109-L126))
- **Architecture**: Conv(32) → Flatten → FC(512) → Dropout → FC(973)
- **Output**: Log probabilities over 973 actions
- **Activation**: Log-softmax (numerical stability)
- **Purpose**: Predict which actions are good

#### 4. **Value Head** ([AntiyoyNNet.py:128-145](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py#L128-L145))
- **Architecture**: Conv(16) → Flatten → FC(256) → Dropout → FC(1)
- **Output**: Single value in [-1, 1]
- **Activation**: Tanh
- **Purpose**: Evaluate position quality

## Hyperparameters

### Network Architecture ([AntiyoyNNet.py](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py))

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `num_channels` | 256 | 128-512 | Network width (capacity) |
| `num_res_blocks` | 5 | 3-15 | Network depth (complexity) |
| `dropout` | 0.3 | 0.1-0.5 | Regularization strength |

### Training Parameters ([NNet.py:29-66](alpha-zero/antiyoy/pytorch/NNet.py#L29-L66))

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `lr` (learning rate) | 0.001 | 0.0001-0.01 | Training speed |
| `epochs` | 10 | 5-20 | Convergence per iteration |
| `batch_size` | 64 | 32-256 | Gradient stability |

### Self-Play Parameters ([main.py:33-119](alpha-zero/main.py#L33-L119))

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `numMCTSSims` | 50 | 25-400 | Search depth |
| `numEps` | 100 | 50-200 | Training data per iteration |
| `arenaCompare` | 40 | 20-100 | Evaluation reliability |

## How to Modify the Architecture

### Making the Network Wider

**When**: Network is underfitting (high loss on both train and validation)

**How**: Increase `num_channels` in [NNet.py:54](alpha-zero/antiyoy/pytorch/NNet.py#L54)

```python
'num_channels': 512,  # Increased from 256
```

**Trade-offs**:
- ✓ More capacity to learn complex patterns
- ✗ Slower training
- ✗ More memory usage
- ✗ May overfit with small datasets

### Making the Network Deeper

**When**: Need to capture more complex strategic patterns

**How**: Increase `num_res_blocks` in [NNet.py:60](alpha-zero/antiyoy/pytorch/NNet.py#L60)

```python
'num_res_blocks': 10,  # Increased from 5
```

**Trade-offs**:
- ✓ Can learn deeper strategic concepts
- ✗ Slower training
- ✗ Requires more careful tuning
- ✗ May overfit

### Adjusting Regularization

**When**: Network is overfitting (train loss << validation loss)

**How**: Increase `dropout` in [NNet.py:44](alpha-zero/antiyoy/pytorch/NNet.py#L44)

```python
'dropout': 0.5,  # Increased from 0.3
```

**Trade-offs**:
- ✓ Prevents overfitting
- ✗ May prevent learning if too high
- ✗ Slower convergence

### Changing Policy/Value Head Size

**When**: Heads are bottleneck (rest of network well-trained but poor predictions)

**How**: Modify FC layer sizes in [AntiyoyNNet.py:120-123](alpha-zero/antiyoy/pytorch/AntiyoyNNet.py#L120-L123)

```python
# Policy head - increase capacity
self.policy_fc1 = nn.Linear(policy_flat_size, 1024)  # Was 512
self.policy_fc2 = nn.Linear(1024, self.action_size)

# Value head - increase capacity
self.value_fc1 = nn.Linear(value_flat_size, 512)  # Was 256
```

**Trade-offs**:
- ✓ More capacity for final predictions
- ✗ Slight slowdown
- ✗ More parameters to train

## Advanced Modifications

### 1. Add Batch Normalization to Heads

```python
# In policy head
self.policy_bn = nn.BatchNorm1d(512)

# In forward():
pi = self.policy_bn(self.policy_fc1(pi))
```

**Effect**: More stable training, especially with deeper networks

### 2. Use Different Activation Functions

```python
# Replace ReLU with LeakyReLU
out = F.leaky_relu(out, negative_slope=0.01)
```

**Effect**: Helps with dead neurons, may improve learning

### 3. Add Attention Mechanisms

```python
class SelfAttention(nn.Module):
    # Implement attention to focus on important board regions
    pass
```

**Effect**: Better focus on strategically important areas

### 4. Increase Conv Filters in Heads

```python
# More filters for richer features
self.policy_conv = nn.Conv2d(self.num_channels, 64, 1)  # Was 32
self.value_conv = nn.Conv2d(self.num_channels, 32, 1)   # Was 16
```

**Effect**: More information for final prediction layers

## Training Tips

### Starting Configuration (Fast Testing)

Good for quick experiments and testing:

```python
# NNet.py
'num_channels': 128,
'num_res_blocks': 3,
'batch_size': 64,

# main.py
'numMCTSSims': 25,
'numEps': 50,
'arenaCompare': 20,
```

**Expected**: ~5-10 minutes per iteration on GPU

### Balanced Configuration (Recommended)

Good balance of speed and performance:

```python
# NNet.py (default values)
'num_channels': 256,
'num_res_blocks': 5,
'batch_size': 64,

# main.py (default values)
'numMCTSSims': 50,
'numEps': 100,
'arenaCompare': 40,
```

**Expected**: ~15-30 minutes per iteration on GPU

### Strong Play Configuration (Serious Training)

For best final performance:

```python
# NNet.py
'num_channels': 512,
'num_res_blocks': 10,
'batch_size': 128,

# main.py
'numMCTSSims': 200,
'numEps': 200,
'arenaCompare': 100,
```

**Expected**: ~1-2 hours per iteration on GPU

## Monitoring Training

### Key Metrics to Watch

1. **Policy Loss** (should decrease over time)
   - Initial: ~6.9 (log(973) ≈ 6.88)
   - Good training: Decreases to 2-4
   - Excellent: Below 2

2. **Value Loss** (should decrease over time)
   - Initial: ~0.5-1.0
   - Good training: Decreases to 0.2-0.4
   - Excellent: Below 0.2

3. **Arena Win Rate** (should improve over time)
   - Random baseline: ~50%
   - Learning: 55-60%
   - Strong: 70-80%
   - Excellent: >90%

### Troubleshooting

| Problem | Symptom | Solution |
|---------|---------|----------|
| **Not learning** | Losses stay high | Increase learning rate or network size |
| **Overfitting** | Train loss << val loss | Increase dropout, reduce network size |
| **Too slow** | >1 hour per iteration | Reduce MCTS sims, network size, or episodes |
| **Unstable training** | Loss oscillates wildly | Reduce learning rate, increase batch size |
| **Out of memory** | CUDA OOM error | Reduce batch size or network size |

## File Structure

```
alpha-zero/
├── antiyoy/
│   └── pytorch/
│       ├── AntiyoyNNet.py      # Neural network architecture ⭐
│       └── NNet.py             # Training wrapper ⭐
├── main.py                     # Training script ⭐
├── test_neural_network.py      # Tests
└── NEURAL_NETWORK_GUIDE.md     # This file
```

⭐ = Files you'll likely modify for experimentation

## Quick Start

### 1. Test the Network

```bash
python3 alpha-zero/test_neural_network.py
```

Should see: "✓ ALL TESTS PASSED!"

### 2. Start Training

```bash
python3 alpha-zero/main.py
```

Watch the output for:
- Self-play progress
- Training loss decreasing
- Arena evaluation results

### 3. Resume Training

Modify [main.py:115](alpha-zero/main.py#L115):

```python
'load_model': True,
```

Then run again:

```bash
python3 alpha-zero/main.py
```

### 4. Adjust for Your Hardware

**CPU Only** (slow):
```python
'num_channels': 128,
'numMCTSSims': 25,
'batch_size': 32,
```

**GPU Available** (fast):
```python
'num_channels': 256,  # or 512
'numMCTSSims': 100,
'batch_size': 128,
```

## Performance Expectations

### Hardware Requirements

| Hardware | Time per Iteration | Recommended Config |
|----------|-------------------|-------------------|
| CPU Only | 1-3 hours | num_channels=128, sims=25 |
| Mid GPU (GTX 1060) | 20-40 minutes | num_channels=256, sims=50 |
| High GPU (RTX 3080) | 10-20 minutes | num_channels=512, sims=100 |
| Very High GPU (A100) | 5-10 minutes | num_channels=512, sims=200 |

### Training Timeline

| Iterations | Playing Strength | Time (Mid GPU) |
|-----------|-----------------|----------------|
| 0-10 | Random/Learning rules | 4-7 hours |
| 10-50 | Basic tactics | 1-2 days |
| 50-200 | Good strategy | 1-2 weeks |
| 200-500 | Strong play | 2-4 weeks |
| 500-1000 | Expert level | 1-2 months |

## Comparison to AlphaZero

| Aspect | AlphaZero (Chess) | Our Implementation |
|--------|------------------|-------------------|
| Board Size | 8×8 | 6×6 |
| Input Channels | ~20 | 22 |
| Actions | ~4000 | 973 |
| Residual Blocks | 20-40 | 5 (configurable) |
| Filters | 256-512 | 256 (configurable) |
| MCTS Simulations | 800 | 50 (configurable) |

Our implementation is scaled appropriately for Antiyoy's complexity - similar to AlphaZero's approach but adapted for the specific game.

## Next Steps

1. ✅ Test the network works (`test_neural_network.py`)
2. Start with fast config for initial testing
3. Monitor training for a few iterations
4. Adjust hyperparameters based on results
5. Scale up when satisfied with setup
6. Train for 500-1000 iterations for strong play

## References

- [AlphaZero Paper](https://arxiv.org/abs/1712.01815)
- [Residual Networks](https://arxiv.org/abs/1512.03385)
- [alpha-zero-general](https://github.com/suragnair/alpha-zero-general)

---

**Good luck with training! The network architecture is flexible and well-commented for easy modification.**
