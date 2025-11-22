import logging
import math
import sys
import numpy as np

EPS = 1e-8

log = logging.getLogger(__name__)

class MCTS():
    """
    This class handles the MCTS tree.
    """

    def __init__(self, game, nnet, args):
        self.game = game
        self.nnet = nnet
        self.args = args
        self.Qsa = {}  # stores Q values for s,a (as defined in the paper)
        self.Nsa = {}  # stores #times edge s,a was visited
        self.Ns = {}  # stores #times board s was visited
        self.Ps = {}  # stores initial policy (returned by neural net)

        self.Es = {}  # stores game.getGameEnded ended for board s
        self.Vs = {}  # stores game.getValidMoves for board s

        # Diagnostics (enable with args.verbose)
        self.max_depth_reached = 0
        self.terminal_depths = []
        self.state_revisits = 0

    def getActionProb(self, canonicalBoard, temp=1):
        """
        This function performs numMCTSSims simulations of MCTS starting from
        canonicalBoard.

        Returns:
            probs: a policy vector where the probability of the ith action is
                   proportional to Nsa[(s,a)]**(1./temp)
        """
        # Reset diagnostics
        self.max_depth_reached = 0
        self.terminal_depths = []
        self.state_revisits = 0

        # Add Dirichlet noise to root node for exploration (AlphaZero technique)
        # This encourages exploration of less-visited moves during self-play
        s = self.game.stringRepresentation(canonicalBoard)

        for i in range(self.args.numMCTSSims):
            # Apply Dirichlet noise to root policy on first iteration
            if i == 0 and s in self.Ps:
                # Get Dirichlet noise parameters from args (with defaults)
                dirichlet_alpha = getattr(self.args, 'dirichletAlpha', 0.3)
                exploration_fraction = getattr(self.args, 'explorationFraction', 0.25)

                # Only add noise if we want exploration (temp > 0)
                if temp > 0:
                    valids = self.game.getValidMoves(canonicalBoard, 1)
                    num_valid_moves = int(np.sum(valids))

                    # Generate Dirichlet noise for valid moves only
                    noise = np.random.dirichlet([dirichlet_alpha] * num_valid_moves)

                    # Create noise array matching action size
                    noise_array = np.zeros(len(valids))
                    noise_array[valids > 0] = noise

                    # Mix policy with noise: (1-ε)p + ε*noise
                    self.Ps[s] = (1 - exploration_fraction) * self.Ps[s] + exploration_fraction * noise_array

            self.search(canonicalBoard)

        # # Print diagnostics if verbose mode enabled
        # verbose = getattr(self.args, 'verbose', False)
        # if verbose:
        #     if self.terminal_depths:
        #         avg_terminal_depth = sum(self.terminal_depths) / len(self.terminal_depths)
        #         log.info(f"MCTS Stats: max_depth={self.max_depth_reached}, "
        #                 f"terminals_found={len(self.terminal_depths)}, "
        #                 f"avg_terminal_depth={avg_terminal_depth:.1f}, "
        #                 f"state_revisits={self.state_revisits}, "
        #                 f"unique_states={len(self.Es)}")
        #     else:
        #         log.warning(f"MCTS Stats: max_depth={self.max_depth_reached}, "
        #                    f"terminals_found=0, "
        #                    f"state_revisits={self.state_revisits}, "
        #                    f"unique_states={len(self.Es)}")

        s = self.game.stringRepresentation(canonicalBoard)
        counts = [self.Nsa[(s, a)] if (s, a) in self.Nsa else 0 for a in range(self.game.getActionSize())]

        if temp == 0:
            bestAs = np.array(np.argwhere(counts == np.max(counts))).flatten()
            if len(bestAs) == 0:
                # All counts are NaN or invalid - fall back to uniform distribution
                log.error("All visit counts are invalid (NaN), using uniform distribution")
                valids = self.game.getValidMoves(canonicalBoard, 1)
                probs = valids / np.sum(valids)
                return probs.tolist()
            bestA = np.random.choice(bestAs)
            probs = [0] * len(counts)
            probs[bestA] = 1
            return probs

        counts = [x ** (1. / temp) for x in counts]
        counts_sum = float(sum(counts))

        if counts_sum > 1e-8:  # Avoid division by zero
            probs = [x / counts_sum for x in counts]
        else:
            # Fallback: use valid moves uniformly
            log.error("MCTS visit counts sum to zero, using uniform distribution")
            valids = self.game.getValidMoves(canonicalBoard, 1)
            probs = (valids / np.sum(valids)).tolist()

        return probs

    def search(self, canonicalBoard, depth=0):
        """
        This function performs one iteration of MCTS. It is recursively called
        till a leaf node is found. The action chosen at each node is one that
        has the maximum upper confidence bound as in the paper.

        Once a leaf node is found, the neural network is called to return an
        initial policy P and a value v for the state. This value is propagated
        up the search path. In case the leaf node is a terminal state, the
        outcome is propagated up the search path. The values of Ns, Nsa, Qsa are
        updated.

        NOTE: the return values are the negative of the value of the current
        state. This is done since v is in [-1,1] and if v is the value of a
        state for the current player, then its value is -v for the other player.

        Args:
            canonicalBoard: current board state
            depth: recursion depth (for safety check)

        Returns:
            v: the negative of the value of the current canonicalBoard
        """

        # Track max depth
        if depth > self.max_depth_reached:
            self.max_depth_reached = depth

        # Safety check: MAX_GAME_TURNS is 50
        # Allow generous depth for untrained network exploration
        if depth > 100:
            # Use heuristic evaluation instead of treating as draw
            # This provides meaningful training signal even at max depth
            if hasattr(self.game, 'evaluatePosition'):
                heuristic_value = self.game.evaluatePosition(canonicalBoard, 1)

                # Apply weighting factor to indicate less certainty than true terminals
                # Default weight of 0.5 means heuristic evals are treated as "softer" signals
                weight = getattr(self.args, 'heuristic_weight', 0.5)
                weighted_value = weight * heuristic_value

                if depth % 100 == 1:  # Log occasionally to avoid spam
                    log.info(f"MCTS max depth ({depth}): Using heuristic eval = {heuristic_value:.3f}, "
                            f"weighted = {weighted_value:.3f} (weight={weight})")

                return -weighted_value
            else:
                # Fallback to draw if evaluatePosition not available
                log.warning(f"MCTS search depth exceeded 1000 (depth={depth}). Forcing draw.")
                return 0

        s = self.game.stringRepresentation(canonicalBoard)

        # Check for state revisits
        if s in self.Ps:
            self.state_revisits += 1

        if s not in self.Es:
            self.Es[s] = self.game.getGameEnded(canonicalBoard, 1)
        if self.Es[s] != 0:
            # terminal node - record depth
            self.terminal_depths.append(depth)
            return -self.Es[s]

        if s not in self.Ps:
            # leaf node
            self.Ps[s], v = self.nnet.predict(canonicalBoard)
            valids = self.game.getValidMoves(canonicalBoard, 1)
            self.Ps[s] = self.Ps[s] * valids  # masking invalid moves
            sum_Ps_s = np.sum(self.Ps[s])
            if sum_Ps_s > 0 and not np.isnan(sum_Ps_s):
                self.Ps[s] /= sum_Ps_s  # renormalize
            else:
                log.error(f"Invalid policy sum ({sum_Ps_s}), using uniform over valid moves")
                self.Ps[s] = valids / np.sum(valids)

            self.Vs[s] = valids
            self.Ns[s] = 0
            return -v

        valids = self.Vs[s]
        cur_best = -float('inf')
        best_act = -1

        # pick the action with the highest upper confidence bound
        for a in range(self.game.getActionSize()):
            if valids[a]:
                if (s, a) in self.Qsa:
                    u = self.Qsa[(s, a)] + self.args.cpuct * self.Ps[s][a] * math.sqrt(self.Ns[s]) / (
                            1 + self.Nsa[(s, a)])
                else:
                    u = self.args.cpuct * self.Ps[s][a] * math.sqrt(self.Ns[s] + EPS)  # Q = 0 ?

                if u > cur_best:
                    cur_best = u
                    best_act = a

        a = best_act
        next_s, next_player = self.game.getNextState(canonicalBoard, 1, a)
        next_s = self.game.getCanonicalForm(next_s, next_player)

        v = self.search(next_s, depth + 1)

        if (s, a) in self.Qsa:
            self.Qsa[(s, a)] = (self.Nsa[(s, a)] * self.Qsa[(s, a)] + v) / (self.Nsa[(s, a)] + 1)
            self.Nsa[(s, a)] += 1

        else:
            self.Qsa[(s, a)] = v
            self.Nsa[(s, a)] = 1

        self.Ns[s] += 1
        return -v
