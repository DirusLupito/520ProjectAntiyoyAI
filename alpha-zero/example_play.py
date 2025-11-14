"""
example_play.py - Example of playing Antiyoy with random agents

This script demonstrates how to use the Antiyoy game implementation
to play a full game between two random agents.
"""

import sys
import os
import numpy as np

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from antiyoy.AntiyoyGame import AntiyoyGame


def play_random_game(max_turns=100, verbose=True):
    """
    Play a full game between two random agents.

    Args:
        max_turns: Maximum number of turns before declaring a draw
        verbose: Whether to print game progress

    Returns:
        Result for player 1 (1 for win, -1 for loss, 1e-4 for draw)
    """
    game = AntiyoyGame()
    board = game.getInitBoard()
    player = 1
    turn_count = 0
    action_count = 0

    if verbose:
        print("\n" + "=" * 60)
        print("ANTIYOY - RANDOM vs RANDOM")
        print("=" * 60)
        game.display(board)

    while True:
        # Get valid moves
        valid_moves = game.getValidMoves(board, player)
        valid_indices = np.where(valid_moves > 0)[0]

        if len(valid_indices) == 0:
            if verbose:
                print(f"\nNo valid moves for player {player}!")
            break

        # Choose random move (with bias towards non-end-turn actions)
        # This makes games more interesting
        end_turn_action = game.getActionSize() - 1
        non_end_turn_actions = valid_indices[valid_indices != end_turn_action]

        if len(non_end_turn_actions) > 0 and np.random.random() < 0.7:
            # 70% chance to take a non-end-turn action if available
            action = np.random.choice(non_end_turn_actions)
        else:
            # Otherwise, pick any valid action (including end turn)
            action = np.random.choice(valid_indices)

        # Decode action type for display
        action_type = "END TURN"
        if action < game.height * game.width * 20:
            action_type = "MOVE"
        elif action < game.getActionSize() - 1:
            action_type = "BUILD"

        if verbose and action_type != "END TURN":
            print(f"\nTurn {turn_count + 1}, Action {action_count + 1}: Player {player} performs {action_type} (action {action})")

        # Apply move
        next_board, next_player = game.getNextState(board, player, action)

        # Check if turn ended
        if next_player != player:
            turn_count += 1
            action_count = 0

            if verbose:
                print(f"\n{'='*60}")
                print(f"End of turn {turn_count} - Next player: {next_player}")
                print(f"{'='*60}")
                game.display(next_board)

            # Check turn limit
            if turn_count >= max_turns:
                if verbose:
                    print(f"\nReached maximum turns ({max_turns}). Game is a draw.")
                return 1e-4
        else:
            action_count += 1

        # Update state
        board = next_board
        player = next_player

        # Check if game ended
        result = game.getGameEnded(board, 1)  # Check from player 1's perspective
        if result != 0:
            if verbose:
                print(f"\n{'='*60}")
                print(f"GAME OVER after {turn_count} turns!")
                print(f"{'='*60}")
                if result == 1:
                    print("Player 1 (RED) wins!")
                elif result == -1:
                    print("Player 2 (BLUE) wins!")
                else:
                    print("Game is a draw!")
                print(f"{'='*60}\n")

            return result

    # If we exited the loop without a result, it's a draw
    return 1e-4


def play_multiple_games(num_games=10):
    """
    Play multiple games and collect statistics.

    Args:
        num_games: Number of games to play

    Returns:
        Dictionary with statistics
    """
    print(f"\nPlaying {num_games} games...\n")

    results = {
        'player1_wins': 0,
        'player2_wins': 0,
        'draws': 0
    }

    for i in range(num_games):
        print(f"Game {i + 1}/{num_games}...", end=" ")
        result = play_random_game(max_turns=50, verbose=False)

        if result == 1:
            results['player1_wins'] += 1
            print("Player 1 wins")
        elif result == -1:
            results['player2_wins'] += 1
            print("Player 2 wins")
        else:
            results['draws'] += 1
            print("Draw")

    print("\n" + "=" * 60)
    print("STATISTICS")
    print("=" * 60)
    print(f"Player 1 wins: {results['player1_wins']} ({results['player1_wins']/num_games*100:.1f}%)")
    print(f"Player 2 wins: {results['player2_wins']} ({results['player2_wins']/num_games*100:.1f}%)")
    print(f"Draws:         {results['draws']} ({results['draws']/num_games*100:.1f}%)")
    print("=" * 60 + "\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Play Antiyoy with random agents')
    parser.add_argument('--games', type=int, default=1, help='Number of games to play')
    parser.add_argument('--verbose', action='store_true', help='Show detailed game output')
    parser.add_argument('--max-turns', type=int, default=50, help='Maximum turns per game')

    args = parser.parse_args()

    if args.games == 1:
        # Play single game with full output
        result = play_random_game(max_turns=args.max_turns, verbose=True)
    else:
        # Play multiple games and show statistics
        results = play_multiple_games(num_games=args.games)
