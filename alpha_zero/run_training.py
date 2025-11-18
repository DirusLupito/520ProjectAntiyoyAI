#!/usr/bin/env python3
"""
Robust training runner that automatically restarts from checkpoints on failure.

This script wraps the main training loop with automatic recovery:
- Catches crashes and exceptions
- Automatically restarts from the most recent checkpoint
- Logs all failures for debugging
- Continues until training completes or manual termination
"""

import sys
# Increase Python recursion limit to reduce RecursionError in deep recursion paths
# (keep this moderate to avoid C stack overflow). Adjust if necessary.
sys.setrecursionlimit(2000)
import time
import logging
import traceback
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('training_runner.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

def run_training():
    """Run the training script and return exit code."""
    from alpha_zero import main
    try:
        main.main()
        return 0
    except KeyboardInterrupt:
        log.info("Training interrupted by user (Ctrl+C)")
        return -1
    except Exception as e:
        log.error(f"Training crashed with {type(e).__name__}: {e}")
        log.error(traceback.format_exc())
        return 1

def main():
    """Main runner loop with automatic restart."""
    attempt = 0
    total_crashes = 0

    log.info("=" * 80)
    log.info("Starting robust training runner")
    log.info("Training will automatically restart from checkpoints on failure")
    log.info("Press Ctrl+C to stop")
    log.info("=" * 80)

    while True:
        attempt += 1
        log.info(f"\n{'='*80}")
        log.info(f"Training attempt #{attempt} (Total crashes: {total_crashes})")
        log.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log.info(f"{'='*80}\n")

        exit_code = run_training()

        if exit_code == 0:
            # Training completed successfully
            log.info("\n" + "=" * 80)
            log.info("Training completed successfully!")
            log.info("=" * 80)
            break
        elif exit_code == -1:
            # User interrupted
            log.info("\n" + "=" * 80)
            log.info("Training stopped by user")
            log.info("=" * 80)
            break
        else:
            # Crash - restart
            total_crashes += 1
            log.warning(f"\n{'='*80}")
            log.warning(f"Training crashed! This was crash #{total_crashes}")
            log.warning("Waiting 5 seconds before restarting from checkpoint...")
            log.warning(f"{'='*80}\n")

            # Brief pause before restart
            time.sleep(5)

            # Continue to next iteration (will restart training)
            log.info("Restarting training from most recent checkpoint...")

if __name__ == '__main__':
    main()
