import logging

from tqdm import tqdm

log = logging.getLogger(__name__)


class Arena():
    """
    An Arena class where any 2 agents can be pit against each other.
    """

    def __init__(self, player1, player2, game, display=None):
        """
        Input:
            player 1,2: two functions that takes board as input, return action
            game: Game object
            display: a function that takes board as input and prints it (e.g.
                     display in othello/OthelloGame). Is necessary for verbose
                     mode.

        see othello/OthelloPlayers.py for an example. See pit.py for pitting
        human players/other baselines with each other.
        """
        self.player1 = player1
        self.player2 = player2
        self.game = game
        self.display = display

    def playGame(self, verbose=False, debug=False):
        """
        Executes one episode of a game.

        Returns:
            game_result: dict containing:
                - winner: 1 if player1 won, -1 if player2 won, or draw value
                - turns: number of turns played
                - final_eval_p1: position evaluation from player1's perspective
                - final_eval_p2: position evaluation from player2's perspective
        """
        players = [self.player2, None, self.player1]
        curPlayer = 1
        board = self.game.getInitBoard()
        it = 0

        for player in players[0], players[2]:
            if hasattr(player, "startGame"):
                player.startGame()

        if debug:
            log.info(f"[Arena] Starting new game")

        while self.game.getGameEnded(board, curPlayer) == 0:
            it += 1
            if verbose:
                print("Turn ", str(it), "Player ", str(curPlayer))

            if debug and it % 10 == 0:
                # Show position evaluation every 10 turns
                eval_p1 = self.game.evaluatePosition(board, 1)
                eval_p2 = self.game.evaluatePosition(board, -1)
                log.info(f"[Arena] Turn {it}: eval_p1={eval_p1:.3f}, eval_p2={eval_p2:.3f}")

            action = players[curPlayer + 1](self.game.getCanonicalForm(board, curPlayer))

            valids = self.game.getValidMoves(self.game.getCanonicalForm(board, curPlayer), 1)

            if valids[action] == 0:
                log.error(f'Action {action} is not valid!')
                log.debug(f'valids = {valids}')
                assert valids[action] > 0

            # Notifying the opponent for the move
            opponent = players[-curPlayer + 1]
            if hasattr(opponent, "notify"):
                opponent.notify(board, action)

            board, curPlayer = self.game.getNextState(board, curPlayer, action)

        for player in players[0], players[2]:
            if hasattr(player, "endGame"):
                player.endGame()

        # Get final game result
        game_ended_value = self.game.getGameEnded(board, 1)
        winner = curPlayer * self.game.getGameEnded(board, curPlayer)

        # Evaluate final position from both players' perspectives
        final_eval_p1 = self.game.evaluatePosition(board, 1)
        final_eval_p2 = self.game.evaluatePosition(board, -1)

        if verbose or debug:
            # Player 1 = Previous/Old network (P), Player 2 = New network (N)
            result_str = "PREVIOUS (P) WINS" if winner == 1 else "NEW (N) WINS" if winner == -1 else f"DRAW ({game_ended_value})"
            print(f"\n{'='*60}")
            print(f"Game over: Turn {it}, Result: {result_str}")
            print(f"  Final eval P (old): {final_eval_p1:.3f}, N (new): {final_eval_p2:.3f}")
            print(f"  (Board ownership: P=1, N=2)")
            print(f"{'='*60}")

            # Print final board state using Scenario.printMap()
            # Convert from canonical form (always player 1 perspective) to actual board state
            try:
                # Import Board to access from_numpy
                from alpha_zero.antiyoy.AntiyoyLogic import Board

                # Convert numpy board to Board object (use player 1 as reference)
                board_obj = Board.from_numpy(board, player=1)

                # Print the actual game scenario
                print("\nFinal Board State:")
                board_obj.scenario.printMap()
                print("")
            except Exception as e:
                log.error(f"Failed to print board state: {e}")
                # Fallback to built-in display if available
                if hasattr(self.game, 'display'):
                    self.game.display(board)

        if debug:
            log.info(f"[Arena] Game finished in {it} turns, winner={winner}, "
                    f"eval_p1={final_eval_p1:.3f}, eval_p2={final_eval_p2:.3f}")

        return {
            'winner': winner,
            'turns': it,
            'final_eval_p1': final_eval_p1,
            'final_eval_p2': final_eval_p2,
            'game_ended_value': game_ended_value
        }

    def playGames(self, num, verbose=False, debug=False):
        """
        Plays num games, alternating which player goes first each game.

        Game 1: player1 (PREVIOUS) goes first
        Game 2: player2 (NEW) goes first
        Game 3: player1 (PREVIOUS) goes first
        ...and so on

        Returns:
            oneWon: games won by player1 (PREVIOUS network)
            twoWon: games won by player2 (NEW network)
            draws:  games won by nobody

        If debug=True, also logs detailed statistics.
        """

        oneWon = 0
        twoWon = 0
        draws = 0

        # Track detailed statistics
        total_turns = []
        p1_evals = []
        p2_evals = []
        draw_results = []

        # Store original players
        original_player1 = self.player1
        original_player2 = self.player2

        for game_num in tqdm(range(num), desc="Arena.playGames"):
            # Alternate who goes first each game
            if game_num % 2 == 1:
                # Odd games: swap so player2 (NEW) goes first
                self.player1, self.player2 = self.player2, self.player1

            result = self.playGame(verbose=verbose, debug=debug)

            # Extract winner from result dict
            winner = result['winner']

            # Count wins relative to ORIGINAL player assignments
            # (accounting for the swap on odd games)
            if game_num % 2 == 0:
                # Even games: normal assignment (player1 = PREVIOUS went first)
                if winner == 1:
                    oneWon += 1
                elif winner == -1:
                    twoWon += 1
                else:
                    draws += 1
                    draw_results.append(result['game_ended_value'])
            else:
                # Odd games: players were swapped (player2 = NEW went first as player1)
                if winner == 1:
                    twoWon += 1  # player1 won, but it's actually NEW after swap
                elif winner == -1:
                    oneWon += 1  # player2 won, but it's actually PREVIOUS after swap
                else:
                    draws += 1
                    draw_results.append(result['game_ended_value'])

                # Restore original assignment for next game
                self.player1, self.player2 = original_player1, original_player2

            # Track statistics
            total_turns.append(result['turns'])
            p1_evals.append(result['final_eval_p1'])
            p2_evals.append(result['final_eval_p2'])

            if debug and (game_num + 1) % 5 == 0:
                log.info(f"[Arena] Game {game_num+1}/{num}: PREV={oneWon}, NEW={twoWon}, Draws={draws}")

        # Ensure players are restored to original
        self.player1 = original_player1
        self.player2 = original_player2

        # Log detailed statistics
        if debug or draws > 0:
            import numpy as np
            avg_turns = np.mean(total_turns)
            avg_p1_eval = np.mean(p1_evals)
            avg_p2_eval = np.mean(p2_evals)

            log.info(f"[Arena] ========== ARENA RESULTS ==========")
            log.info(f"[Arena] PREVIOUS wins: {oneWon}/{num} ({100*oneWon/num:.1f}%)")
            log.info(f"[Arena] NEW wins: {twoWon}/{num} ({100*twoWon/num:.1f}%)")
            log.info(f"[Arena] Draws: {draws}/{num} ({100*draws/num:.1f}%)")
            log.info(f"[Arena] Average game length: {avg_turns:.1f} turns")
            log.info(f"[Arena] Average final eval P (old): {avg_p1_eval:.3f}")
            log.info(f"[Arena] Average final eval N (new): {avg_p2_eval:.3f}")
            if draws > 0:
                log.info(f"[Arena] Draw results: {draw_results}")
            log.info(f"[Arena] =====================================")

        return oneWon, twoWon, draws
