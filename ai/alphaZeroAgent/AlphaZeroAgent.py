"""
AlphaZeroAgent.py - AI agent using trained AlphaZero neural network

This agent implements the playTurn(scenario, faction) interface
using a trained AlphaZero neural network to select actions.

The agent can operate in two modes:
1. MCTS mode (strong but slow): Uses MCTS + neural network for strong play
2. Policy-only mode (fast but weaker): Uses only neural network policy

Usage:
    from ai.alphaZeroAgent.AlphaZeroAgent import AlphaZeroAgent

    # Create agent (loads trained checkpoint)
    agent = AlphaZeroAgent(
        checkpoint_folder='alpha_zero/temp',
        checkpoint_file='best.pth.tar',
        use_mcts=True,  # False for faster but weaker play
        num_mcts_sims=50  # Number of MCTS simulations if use_mcts=True
    )

    # Use in game
    actions = agent.playTurn(scenario, faction)
"""

import sys
import os
import numpy as np

from alpha_zero.antiyoy.AntiyoyGame import AntiyoyGame
from alpha_zero.antiyoy.AntiyoyLogic import Board
from alpha_zero.antiyoy.pytorch.NNet import NNetWrapper
from alpha_zero.MCTS import MCTS
from azg.utils import dotdict


class AlphaZeroAgent:
    """
    AI agent that uses a trained AlphaZero neural network to play Antiyoy.

    This agent bridges between the alpha-zero framework (which works with
    numpy arrays and action indices) and the original game code (which works
    with Scenario objects and Action objects).
    """

    def __init__(
        self,
        checkpoint_folder='temp/',
        checkpoint_file='best.pth.tar',
        use_mcts=True,
        num_mcts_sims=100,
        temperature=.4  # 0 = greedy, >0 = stochastic
    ):
        """
        Initialize the AlphaZero agent.

        Args:
            checkpoint_folder: Path to folder containing trained model
            checkpoint_file: Filename of checkpoint to load
            use_mcts: If True, use MCTS for stronger play (slower)
                     If False, use only neural network policy (faster, weaker)
            num_mcts_sims: Number of MCTS simulations per move (if use_mcts=True)
            temperature: Temperature for move selection
                        0 = always choose best move (greedy)
                        >0 = sample from distribution (stochastic)
        """
        print(f"Initializing AlphaZero agent...")
        print(f"  Checkpoint: {checkpoint_folder}/{checkpoint_file}")
        print(f"  MCTS: {'Enabled' if use_mcts else 'Disabled'}")
        if use_mcts:
            print(f"  MCTS simulations: {num_mcts_sims}")

        # Initialize game and neural network
        self.game = AntiyoyGame()
        self.nnet = NNetWrapper(self.game)

        # Load trained checkpoint
        full_checkpoint_path = os.path.join(
            os.path.dirname(os.curdir),
            checkpoint_folder
        )
        self.nnet.load_checkpoint(full_checkpoint_path, checkpoint_file)
        print(f"✓ Neural network loaded successfully!")

        # Set up MCTS if requested
        self.use_mcts = use_mcts
        self.temperature = temperature

        if use_mcts:
            # Create MCTS args
            mcts_args = dotdict({
                'numMCTSSims': num_mcts_sims,
                'cpuct': 1.0,
            })
            self.mcts = MCTS(self.game, self.nnet, mcts_args)
        else:
            self.mcts = None

        print(f"✓ AlphaZero agent ready!")

    def playTurn(self, scenario, faction, debug=False):
        """
        Generate actions for the AI's turn using the AlphaZero neural network.

        This is the main interface function that's called by the game engine.

        Args:
            scenario: The current game Scenario object
            faction: The Faction object for which to play the turn
            debug: If True, print detailed debug information

        Returns:
            A list of (Action, province) tuples to be executed
        """
        # Determine which player we are (1 or -1)
        player = self._get_player_number(scenario, faction)

        if debug:
            print(f"\n[AlphaZero Debug] Player number: {player}")

        # Get the first active province for this faction
        # (In our alpha-zero setup, we assume one province per faction)
        province = None
        for p in faction.provinces:
            if p.active:
                province = p
                break

        if province is None:
            # No active provinces - return empty action list
            if debug:
                print(f"[AlphaZero Debug] No active provinces - ending turn")
            return []

        if debug:
            print(f"[AlphaZero Debug] Province has {len(province.tiles)} tiles, {province.resources} resources, active={province.active}")

        # Convert scenario to numpy representation
        board = Board(scenario=scenario, current_player=player)
        numpy_board = board.get_numpy_board()

        # Collect actions until we decide to end turn
        all_actions = []
        actions_taken = 0

        while actions_taken < Board.MAX_ACTIONS_PER_TURN:
            # Get canonical form for current player
            canonical_board = self.game.getCanonicalForm(numpy_board, player)

            # Get action probabilities
            if self.use_mcts:
                # Use MCTS for strong play
                action_probs = self.mcts.getActionProb(canonical_board, temp=self.temperature)
            else:
                # Use only neural network policy (faster but weaker)
                action_probs, value = self.nnet.predict(canonical_board)
                if debug:
                    print(f"[AlphaZero Debug] Neural network value prediction: {value}")

            # Ensure action_probs is a numpy array (MCTS returns a list)
            action_probs = np.array(action_probs)

            # Mask invalid actions
            valid_moves = self.game.getValidMoves(canonical_board, 1, debug=debug)
            num_valid = int(np.sum(valid_moves))

            # Prevent END_TURN if we have other valid actions and haven't taken any yet
            if num_valid > 1 and actions_taken == 0:
                end_turn_idx = self.game.action_size - 1
                if valid_moves[end_turn_idx] > 0:
                    valid_moves[end_turn_idx] = 0
                    num_valid = int(np.sum(valid_moves))

                    if debug:
                        print(f"[AlphaZero Debug] END_TURN masked (haven't taken action yet, {num_valid} alternatives exist)")

            if debug:
                print(f"[AlphaZero Debug] Number of valid moves: {num_valid}")
                if num_valid > 0:
                    # Show top 5 valid actions by probability
                    valid_indices = np.where(valid_moves > 0)[0]
                    valid_probs = action_probs[valid_indices]
                    top_5_idx = np.argsort(valid_probs)[-5:][::-1]
                    print(f"[AlphaZero Debug] Top 5 valid actions:")
                    for i in top_5_idx:
                        act_idx = valid_indices[i]
                        prob = valid_probs[i]
                        # Decode action for display
                        if board.is_end_turn_action(act_idx):
                            action_desc = "END_TURN"
                        elif board.decode_move_action(act_idx):
                            from_r, from_c, to_r, to_c = board.decode_move_action(act_idx)
                            action_desc = f"MOVE ({from_r},{from_c})→({to_r},{to_c})"
                        elif board.decode_build_action(act_idx):
                            r, c, unit = board.decode_build_action(act_idx)
                            action_desc = f"BUILD {unit} at ({r},{c})"
                        else:
                            action_desc = "UNKNOWN"
                        print(f"  {i+1}. {action_desc} (prob={prob:.4f})")

            action_probs = action_probs * valid_moves

            # Normalize
            if np.sum(action_probs) > 0:
                action_probs = action_probs / np.sum(action_probs)
            else:
                # No valid moves - end turn
                if debug:
                    print(f"[AlphaZero Debug] No valid moves available - ending turn")
                break

            # Select action
            if self.temperature == 0:
                # Greedy: choose best action
                action_idx = np.argmax(action_probs)
            else:
                # Stochastic: sample from distribution
                action_idx = np.random.choice(len(action_probs), p=action_probs)

            if debug:
                # Show selected action
                if board.is_end_turn_action(action_idx):
                    action_desc = "END_TURN"
                elif board.decode_move_action(action_idx):
                    from_r, from_c, to_r, to_c = board.decode_move_action(action_idx)
                    action_desc = f"MOVE ({from_r},{from_c})→({to_r},{to_c})"
                elif board.decode_build_action(action_idx):
                    r, c, unit = board.decode_build_action(action_idx)
                    action_desc = f"BUILD {unit} at ({r},{c})"
                else:
                    action_desc = "UNKNOWN"
                print(f"[AlphaZero Debug] Selected action: {action_desc} (index={action_idx})")

            # Check if it's end turn action
            if board.is_end_turn_action(action_idx):
                # Explicitly chose to end turn
                if debug:
                    print(f"[AlphaZero Debug] Chose to end turn explicitly")
                break

            # Convert action index to actual Action objects
            action_objects = self._convert_action_to_objects(
                board, action_idx, scenario, province
            )

            if action_objects is None or len(action_objects) == 0:
                # Invalid action or conversion failed - end turn
                if debug:
                    print(f"[AlphaZero Debug] Action conversion failed - ending turn")
                break

            # Add actions to our list
            for action_obj in action_objects:
                all_actions.append((action_obj, province))

            # Apply actions to scenario to keep it in sync
            # (The game engine will also apply them, but we need
            #  to keep our internal state consistent)
            for action_obj in action_objects:
                scenario.applyAction(action_obj, province)

            # Update board state for next iteration
            numpy_board, next_player = self.game.getNextState(
                numpy_board, player, action_idx
            )

            # If player changed, we're done with our turn
            if next_player != player:
                break

            actions_taken += 1

        if debug:
            print(f"[AlphaZero Debug] Returning {len(all_actions)} actions")

        return all_actions

    def _get_player_number(self, scenario, faction):
        """
        Determine which player number (1 or -1) this faction corresponds to.

        In our alpha-zero setup:
        - First faction in scenario.factions = player 1
        - Second faction in scenario.factions = player -1

        Args:
            scenario: Current game scenario
            faction: Our faction

        Returns:
            1 or -1
        """
        try:
            faction_index = scenario.factions.index(faction)
            return 1 if faction_index == 0 else -1
        except ValueError:
            # Faction not found in scenario - default to player 1
            return 1

    def _convert_action_to_objects(self, board, action_idx, scenario, province):
        """
        Convert an action index to actual Action objects.

        Args:
            board: Board object (for decoding)
            action_idx: Integer action index (0-972)
            scenario: Current scenario object
            province: Province to execute action for

        Returns:
            List of Action objects, or None if invalid
        """
        # Try to decode as move action
        move_result = board.decode_move_action(action_idx)
        if move_result is not None:
            from_row, from_col, to_row, to_col = move_result
            try:
                # Use scenario's moveUnit to get Action objects
                action_objects = scenario.moveUnit(from_row, from_col, to_row, to_col)
                return action_objects
            except Exception as e:
                # Move failed (probably invalid)
                return None

        # Try to decode as build action
        build_result = board.decode_build_action(action_idx)
        if build_result is not None:
            row, col, unit_type = build_result
            try:
                # Use scenario's buildUnitOnTile to get Action objects
                action_objects = scenario.buildUnitOnTile(row, col, unit_type, province)
                return action_objects
            except Exception as e:
                # Build failed (probably invalid)
                return None

        # Unknown action type
        return None


# Global agent instance (lazy-loaded, reused across turns)
_global_agent = None
_agent_initialized = False


def _get_or_create_agent():
    """
    Get or create the global AlphaZero agent instance.

    This ensures the agent is only created once and reused across turns,
    which is much more efficient than creating a new agent each turn.

    Returns:
        AlphaZeroAgent instance, or None if checkpoint not found
    """
    global _global_agent, _agent_initialized

    if _agent_initialized:
        return _global_agent

    # Try to create the agent
    try:
        _global_agent = AlphaZeroAgent(
            checkpoint_folder='/home/nrcunard/csc520/520ProjectAntiyoyAI/temp/',
            checkpoint_file='best.pth.tar',
            use_mcts=False,  # Fast mode for gameplay (set to True for stronger play)
            num_mcts_sims=25
        )
        _agent_initialized = True
        print("✓ AlphaZero agent loaded and ready!")
        return _global_agent
    except FileNotFoundError as e:
        print(f"\n⚠ WARNING: AlphaZero checkpoint not found!")
        print(f"  {e}")
        print(f"  The AlphaZero agent will not be able to play.")
        print(f"\n  To train a model, run:")
        print(f"    cd alpha_zero && python3 main.py")
        print(f"\n  The agent will fall back to random moves until a checkpoint is available.\n")
        _agent_initialized = True  # Mark as initialized to avoid repeated warnings
        _global_agent = None
        return None
    except Exception as e:
        print(f"\n⚠ WARNING: Failed to initialize AlphaZero agent!")
        print(f"  Error: {e}")
        print(f"  The agent will fall back to random moves.\n")
        import traceback
        traceback.print_exc()
        _agent_initialized = True
        _global_agent = None
        return None


def playTurn(scenario, faction):
    """
    Standalone playTurn function for integration with AI framework.

    This function implements the standard AI interface expected by
    the game engine. It uses a persistent AlphaZero agent instance
    that's created once and reused across turns for efficiency.

    Args:
        scenario: Current game scenario
        faction: Faction to play for

    Returns:
        List of (Action, province) tuples
    """
    # Get or create the global agent instance
    agent = _get_or_create_agent()

    if agent is None:
        # Checkpoint not found - return empty action list (end turn)
        # This prevents crashes when the model hasn't been trained yet
        return []

    # Use the agent to generate actions
    # Enable debug=True to see detailed output about what the agent is thinking
    return agent.playTurn(scenario, faction, debug=True)
