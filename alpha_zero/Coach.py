import logging
import os
import sys
from collections import deque
from pickle import Pickler, Unpickler
from random import shuffle

import numpy as np
from tqdm import tqdm

from alpha_zero.Arena import Arena
from alpha_zero.MCTS import MCTS

log = logging.getLogger(__name__)


class Coach():
    """
    This class executes the self-play + learning. It uses the functions defined
    in Game and NeuralNet. args are specified in main.py.
    """

    def __init__(self, game, nnet, args):
        self.game = game
        self.nnet = nnet
        self.pnet = self.nnet.__class__(self.game)  # the competitor network
        self.args = args
        self.mcts = MCTS(self.game, self.nnet, self.args)
        self.trainExamplesHistory = []  # history of examples from args.numItersForTrainExamplesHistory latest iterations
        self.skipFirstSelfPlay = False  # can be overriden in loadTrainExamples()

    def executeEpisode(self):
        """
        This function executes one episode of self-play, starting with player 1.
        As the game is played, each turn is added as a training example to
        trainExamples. The game is played till the game ends. After the game
        ends, the outcome of the game is used to assign values to each example
        in trainExamples.

        It uses a temp=1 if episodeStep < tempThreshold, and thereafter
        uses temp=0.

        Returns:
            trainExamples: a list of examples of the form (canonicalBoard, currPlayer, pi,v)
                           pi is the MCTS informed policy vector, v is +1 if
                           the player eventually won the game, else -1.
        """
        trainExamples = []
        board = self.game.getInitBoard()
        self.curPlayer = 1
        episodeStep = 0

        # Track cumulative step rewards for each player
        cumulative_rewards = {1: 0.0, -1: 0.0}

        while True:
            episodeStep += 1

            try:
                log.debug(f"[Episode] Step {episodeStep}: Getting canonical board for player {self.curPlayer}")
                canonicalBoard = self.game.getCanonicalForm(board, self.curPlayer)
                temp = int(episodeStep < self.args.tempThreshold)

                log.debug(f"[Episode] Step {episodeStep}: Calling MCTS.getActionProb (temp={temp})")
                pi = self.mcts.getActionProb(canonicalBoard, temp=temp)

                # Check for NaN/Inf in policy
                if np.any(np.isnan(pi)) or np.any(np.isinf(pi)):
                    log.error(f"[CRITICAL] Invalid policy from MCTS at step {episodeStep}: pi has NaN/Inf")
                    log.error(f"  pi min={np.min(pi)}, max={np.max(pi)}, sum={np.sum(pi)}")
                    raise ValueError("Invalid policy from MCTS")

                log.debug(f"[Episode] Step {episodeStep}: Getting symmetries")
                sym = self.game.getSymmetries(canonicalBoard, pi)
                for b, p in sym:
                    trainExamples.append([b, self.curPlayer, p, None])

                log.debug(f"[Episode] Step {episodeStep}: Selecting action from policy")
                action = np.random.choice(len(pi), p=pi)

                log.debug(f"[Episode] Step {episodeStep}: Applying action {action}")
                board, self.curPlayer = self.game.getNextState(board, self.curPlayer, action)

                # Calculate and accumulate step reward for the player who just moved
                # Note: curPlayer has switched after getNextState, so we need the previous player
                previous_player = -self.curPlayer
                log.debug(f"[Episode] Step {episodeStep}: Calculating step reward")
                step_reward = self.game.getStepReward(board, previous_player)

                # Safety check for NaN/Inf in step rewards
                if np.isnan(step_reward) or np.isinf(step_reward):
                    log.error(f"Invalid step_reward detected: {step_reward} at episodeStep {episodeStep}")
                    step_reward = 0.0

                cumulative_rewards[previous_player] += step_reward

                log.debug(f"[Episode] Step {episodeStep}: Checking if game ended")
                r = self.game.getGameEnded(board, self.curPlayer)

            except Exception as e:
                log.error(f"[CRITICAL] Exception in episode at step {episodeStep}: {type(e).__name__}: {e}")
                log.error(f"  curPlayer={self.curPlayer}, action={action if 'action' in locals() else 'N/A'}")
                log.error(f"  Episode will be terminated early")
                import traceback
                traceback.print_exc()
                raise

            if r != 0:
                # Add cumulative rewards to final outcome
                # Each example gets: (final outcome from their perspective) + (their cumulative reward)
                final_values = []
                for x in trainExamples:
                    outcome = r * ((-1) ** (x[1] != self.curPlayer))
                    cumulative = cumulative_rewards[x[1]]
                    final_value = outcome + cumulative

                    # Safety check for NaN/Inf in final values
                    if np.isnan(final_value) or np.isinf(final_value):
                        log.error(f"Invalid final_value: {final_value} (outcome={outcome}, cumulative={cumulative})")
                        final_value = outcome  # Fall back to just the outcome

                    # Clamp extreme values to prevent gradient explosion
                    final_value = np.clip(final_value, -10.0, 10.0)

                    final_values.append((x[0], x[2], final_value))

                # Log reward statistics for debugging
                avg_p1 = cumulative_rewards[1] / max(1, episodeStep // 2)
                avg_p2 = cumulative_rewards[-1] / max(1, episodeStep // 2)
                log.debug(f"Episode ended: steps={episodeStep}, cumulative_p1={cumulative_rewards[1]:.2f}, "
                         f"cumulative_p2={cumulative_rewards[-1]:.2f}, avg_p1={avg_p1:.3f}, avg_p2={avg_p2:.3f}")

                return final_values

    def learn(self):
        """
        Performs numIters iterations with numEps episodes of self-play in each
        iteration. After every iteration, it retrains neural network with
        examples in trainExamples (which has a maximum length of maxlenofQueue).
        It then pits the new neural network against the old one and accepts it
        only if it wins >= updateThreshold fraction of games.
        """

        # Save initial model as best.pth.tar if it doesn't exist
        best_path = os.path.join(self.args.checkpoint, 'best.pth.tar')
        if not os.path.exists(best_path):
            log.info('Saving initial model as best.pth.tar')
            self.nnet.save_checkpoint(folder=self.args.checkpoint, filename='best.pth.tar')

        for i in range(1, self.args.numIters + 1):
            # bookkeeping
            log.info(f'Starting Iter #{i} ...')
            # examples of the iteration
            if not self.skipFirstSelfPlay or i > 1:
                iterationTrainExamples = deque([], maxlen=self.args.maxlenOfQueue)

                for _ in tqdm(range(self.args.numEps), desc="Self Play"):
                    self.mcts = MCTS(self.game, self.nnet, self.args)  # reset search tree
                    iterationTrainExamples += self.executeEpisode()

                # save the iteration examples to the history 
                self.trainExamplesHistory.append(iterationTrainExamples)

            if len(self.trainExamplesHistory) > self.args.numItersForTrainExamplesHistory:
                log.warning(
                    f"Removing the oldest entry in trainExamples. len(trainExamplesHistory) = {len(self.trainExamplesHistory)}")
                self.trainExamplesHistory.pop(0)
            # backup history to a file
            # NB! the examples were collected using the model from the previous iteration, so (i-1)  
            self.saveTrainExamples(i - 1)

            # shuffle examples before training
            trainExamples = []
            for e in self.trainExamplesHistory:
                trainExamples.extend(e)
            shuffle(trainExamples)

            # training new network, keeping a copy of the old one
            self.nnet.save_checkpoint(folder=self.args.checkpoint, filename='temp.pth.tar')
            self.pnet.load_checkpoint(folder=self.args.checkpoint, filename='temp.pth.tar')
            pmcts = MCTS(self.game, self.pnet, self.args)

            self.nnet.train(trainExamples)
            nmcts = MCTS(self.game, self.nnet, self.args)

            log.info('PITTING AGAINST PREVIOUS VERSION')
            # Use temp=1.0 for arena to add significant randomness and reduce draws
            # temp=0 (greedy) causes many draws when networks are similar
            # temp=1.0 adds substantial randomness for more decisive, varied games
            arena = Arena(lambda x: np.argmax(pmcts.getActionProb(x, temp=.30)),
                          lambda x: np.argmax(nmcts.getActionProb(x, temp=.30)), self.game)
            pwins, nwins, draws = arena.playGames(self.args.arenaCompare, debug=True)

            log.info('NEW/PREV WINS : %d / %d ; DRAWS : %d' % (nwins, pwins, draws))
            if pwins + nwins == 0 or float(nwins) / (pwins + nwins) < self.args.updateThreshold:
                log.info('REJECTING NEW MODEL')
                self.nnet.load_checkpoint(folder=self.args.checkpoint, filename='temp.pth.tar')
            else:
                log.info('ACCEPTING NEW MODEL')
                self.nnet.save_checkpoint(folder=self.args.checkpoint, filename=self.getCheckpointFile(i))
                self.nnet.save_checkpoint(folder=self.args.checkpoint, filename='best.pth.tar')

    def getCheckpointFile(self, iteration):
        return 'checkpoint_' + str(iteration) + '.pth.tar'

    def saveTrainExamples(self, iteration):
        folder = self.args.checkpoint
        if not os.path.exists(folder):
            os.makedirs(folder)
        filename = os.path.join(folder, self.getCheckpointFile(iteration) + ".examples")
        with open(filename, "wb+") as f:
            Pickler(f).dump(self.trainExamplesHistory)
        f.closed

    def loadTrainExamples(self):
        modelFile = os.path.join(self.args.load_folder_file[0], self.args.load_folder_file[1])
        examplesFile = modelFile + ".examples"
        if not os.path.isfile(examplesFile):
            log.warning(f'File "{examplesFile}" with trainExamples not found!')
        else:
            log.info("File with trainExamples found. Loading it...")
            with open(examplesFile, "rb") as f:
                self.trainExamplesHistory = Unpickler(f).load()
            log.info('Loading done!')

            # examples based on the model were already collected (loaded)
            self.skipFirstSelfPlay = True
