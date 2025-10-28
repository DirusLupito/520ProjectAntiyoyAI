import datetime
import os
import time
import pdb
from typing import Dict, List, Optional, Tuple

from game.replays.Replay import Replay
from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction
from ai.AIPersonality import AIPersonality
from tournaments.TournamentStatisticsRecorder import TournamentStatisticsRecorder
from tournaments.AITournamentConfig import AITournamentConfig
from tournaments.GameOutcome import GameOutcome

class AITournamentRunner:
    """
    Runs tournament games according to a provided configuration.
    
    A tournament consists of multiple games played between multiple AI personalities
    over a series of rounds. This class manages the setup, execution, and recording
	of these games based on the specified configuration.
    
    General statistics about the tournament are given at the end of the run,
    and more detailed per-game per-turn statistics can be recorded if enabled.
    
    Replays of every game can also be recorded if enabled.
    
    Each turn of each game can also be optionally displayed as if it were an AI only
    game being run from main.py. This is only recommended for debugging purposes
	as it significantly slows down the tournament.
    
    For a full description of the statistics recorded, see TournamentStatisticsRecorder.
    For a full description of the seed picking modes, see TournamentSeedPicker.
    For a full description of the configuration options, see AITournamentConfig.
    """

    def __init__(self, config: AITournamentConfig) -> None:
        """
        Initializes the tournament runner with the specified configuration.
        Sets up directories for replays and statistics if those features are enabled.
        To ensure unique directories, a timestamp is used in their names.
        A tournament which ran on June 1, 2024 at 14:30:15 would have directories named
		"01-06-2024-14-30-15-tournamentReplays" and "01-06-2024-14-30-15-tournamentStats".
        
        Args:
			config (AITournamentConfig): The configuration for the tournament.
        """

        self.config = config
        # day-month-year-hour-minute-second nomenclature for unique directory names
        dateStamp = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
        
		# Figure out the full paths for replay and statistics directories if needed
        self.replayDirectory = os.path.join(
            os.getcwd(),
            f"{dateStamp}-tournamentReplays"
        ) if config.recordReplays else None
        
        self.statisticsDirectory = os.path.join(
            os.getcwd(),
            f"{dateStamp}-tournamentStats"
        ) if config.trackStatistics else None
        
        self.statisticsRecorder: Optional[TournamentStatisticsRecorder] = None
        # If we were able to set up a statistics directory, it means we want to record stats
        if self.statisticsDirectory is not None:
            self.statisticsRecorder = TournamentStatisticsRecorder(config.personalities, self.statisticsDirectory)
            
		# If we were able to set up a replay directory, it means we want to record replays
        if self.replayDirectory is not None and not os.path.isdir(self.replayDirectory):
            os.makedirs(self.replayDirectory, exist_ok=True)

    def runTournament(self) -> None:
        """
        Handles actually running the tournament and all its games and each of those games' turns.
        Records replays and statistics as configured.
		At the end, displays a summary of the tournament results.
        """
        
		# Figure out what seeds to use for each game based on the seed picker configuration
        seeds = self.config.seedPicker.generateSeeds(self.config.roundCount)
        
		# Keep track of overall outcomes and wins per personality
        outcomes: List[GameOutcome] = []
        winsByPersonality: Dict[str, int] = {p.displayName: 0 for p in self.config.personalities}
        
		# Iterate through each game to be played in the tournament
        for gameIndex in range(self.config.roundCount):
            
			# Get this game's seed
            seed = seeds[gameIndex]
            
			# Set up the factions for this game
            # with descriptive names and colors
            # so the replays are easier to follow
            factions = self._buildFactions()
            
			# Generate the scenario for this game
            scenario = generateRandomScenario(
                self.config.dimension,
                self.config.targetLandTiles,
                factions,
                self.config.initialProvinceSize,
                randomSeed=seed
            )
            
			# If applicable, set up the replay for this game
            replay = None
            if self.config.recordReplays:
                metadata = {
                    "dimension": self.config.dimension,
                    "targetLandTiles": self.config.targetLandTiles,
                    "initialProvinceSize": self.config.initialProvinceSize,
                    "seed": seed,
                    "factions": [
                        {
                            "name": faction.name,
                            "color": faction.color,
                            "aiType": faction.aiType
                        }
                        for faction in factions
                    ]
                }
                replay = Replay.fromScenario(scenario, metadata=metadata)
                
			# If applicable, record the initial state for statistics
            if self.statisticsRecorder is not None:
                self.statisticsRecorder.recordInitialState(factions, gameIndex + 1, seed)
                
			# Run the actual game
            outcome = self._runSingleGame(
                scenario,
                factions,
                replay,
                gameIndex + 1,
                seed
            )
            
			# Track the outcome and record replay/statistics if applicable
            outcomes.append(outcome)
            
            if outcome.winnerName is not None:
                winsByPersonality[outcome.winnerName] += 1
                
            if self.config.recordReplays and replay is not None and self.replayDirectory is not None:
                # In order to save memory and in case a crash happens later,
                # write out the replay to disk immediately after the game
                # rather than waiting until the end of the tournament
                fileName = f"game{gameIndex + 1}.ayrf"
                replayPath = os.path.join(self.replayDirectory, fileName)
                replay.saveToFile(replayPath)
                
        if self.statisticsRecorder is not None:
            # Write out all the statistics files now that the tournament is complete
            self.statisticsRecorder.writeFiles()
            
		# Display the overall tournament summary
        self._displaySummary(outcomes, winsByPersonality, seeds)

    def _buildFactions(self) -> List[Faction]:
        """
        Build the factions for the tournament based on the configured factions.
        Each faction is assigned a unique color from the available color codes.
        We want to try to ensure that no two factions have the same color,
        although if there are more factions than colors, colors will be reused.
        
        See Faction.colorCodesMap for the available colors and the ordering of those colors.
        
        Returns:
			List[Faction]: The list of factions for the tournament.
        """
        
		# Starting with an empty list of factions,
		# we iterate through each personality in the configuration
		# and create a faction for it with a (hopefully) unique color
        factions: List[Faction] = []
        for index, personality in enumerate(self.config.personalities):
            color = list(Faction.colorCodesMap.keys())[index % len(list(Faction.colorCodesMap.keys()))]
            
			# We name the faction after the personality's display name
            # so that its easier to track what AI is playing which faction
            # in replays and statistics
            faction = Faction(name=personality.displayName, color=color, playerType="ai", aiType=personality.aiType)
            factions.append(faction)
            
        return factions

    def _runSingleGame(
        self,
        scenario,
        factions: List[Faction],
        replay: Optional[Replay],
        gameNumber: int,
        seed: Optional[int]
    ) -> GameOutcome:
        """
		Handles the logic for running each individual game in the tournament.
		Loops through turns until a win condition is met (either one faction remains
		or all factions are eliminated).
        
        Args:
			scenario: The scenario to run the game on.
			factions (List[Faction]): The factions participating in the game.
			replay (Optional[Replay]): The replay object to record the game, if any.
			gameNumber (int): The number of the game in the tournament.
			seed (Optional[int]): The seed used for this game's scenario, if any.
            
		Returns:
			GameOutcome: The outcome of the game, including the winner, seed, and number of turns played.
        """
        
        gameOver = False
        turnCounter = 0
        
		# Similar to main.py's game loop,
        # and the logic for handling AI turns
        # with some modifications for various statistic tracking and recording features
        while not gameOver:
            
            activeFactions = [faction for faction in factions if any(province.active for province in faction.provinces)]
            
            if len(activeFactions) <= 1:
                break
            
            currentFaction = scenario.getFactionToPlay()
            
			# If somehow we got a non-AI faction, that's an error
            if currentFaction.playerType != "ai":
                raise RuntimeError("Tournament runner encountered a non-AI faction.")
            
			# If we are displaying games, show the current map and faction info
            # and give the user a chance to break into the debugger
            if self.config.displayGames:
                print(f"\n===== {currentFaction.name}'s Turn ({currentFaction.color}) =====")
                scenario.displayMap()
                print(f"{currentFaction.name} (AI) is thinking...")
                debugInput = input("Press Enter to continue or b to break into debugger: ")
                if debugInput.lower() == "b":
                    pdb.set_trace()
            
			# Get the AI's actions for this turn and time how long it takes
            aiFunction = AIPersonality.implementedAIs[currentFaction.aiType]
            decisionStart = time.perf_counter()
            aiActions = aiFunction(scenario, currentFaction)
            decisionEnd = time.perf_counter()
            
			# Multiply by 1000 to convert seconds to milliseconds
            decisionTimeMs = (decisionEnd - decisionStart) * 1000.0
            
			# Apply the AI's actions to the scenario
            # appliedActions is used to both apply the actions
            # and to record them in the replay if applicable
            appliedActions: List[Tuple] = []
            if aiActions:
                if self.config.displayGames:
                    print(f"{currentFaction.name} (AI) is performing {len(aiActions)} actions...")
                    
                for action, province in aiActions:
                    try:
                        scenario.applyAction(action, province)
                        appliedActions.append((action, province))
                    except Exception as exc:
                        print(f"Warning: Skipping invalid action generated by {currentFaction.name}: {exc}")
            else:
                if self.config.displayGames:
                    print(f"{currentFaction.name} (AI) chose to do nothing.")
            
			# We're done with this turn, so advance to the next turn
            # and record the turn in the replay if applicable
            turnAdvanceActions = scenario.advanceTurn()
            if replay is not None:
                turnReplayActions = list(appliedActions)
                turnReplayActions.extend(turnAdvanceActions)
                replay.recordTurn(scenario, currentFaction, turnReplayActions)
                
			# Keep track of how many turns have been played
            # for the final outcome reporting
            turnCounter += 1
            
			# If applicable, record statistics all the various statistics
            # we're interested in for this turn
            if self.statisticsRecorder is not None:
                self.statisticsRecorder.recordAfterTurn(
                    currentFaction,
                    gameNumber,
                    turnCounter,
                    seed,
                    decisionTimeMs,
                    len(aiActions) if aiActions else 0
                )
        
		# The game is over at this point, we need to figure out
        # who the winner is (if any)
        winnerFaction = None
        for faction in factions:
            if any(province.active for province in faction.provinces):
                winnerFaction = faction
                break
            
		# If we are displaying games, remember to show the final map and winner info
        if self.config.displayGames:
            print("\n===== Game Over =====")
            scenario.displayMap()
            
        if winnerFaction is not None and self.config.displayGames:
            print(f"Winner: {winnerFaction.name} ({winnerFaction.color})")
            
		# We're all done, just need to return the outcome now
        return GameOutcome(
            winnerFaction.name if winnerFaction else None,
            winnerFaction.color if winnerFaction else None,
            seed,
            turnCounter
        )

    def _displaySummary(
        self,
        outcomes: List[GameOutcome],
        winsByPersonality: Dict[str, int],
        seeds: List[Optional[int]]
    ) -> None:
        """
        Displays a summary of the tournament results.
        This will be printed to the console no matter what,
		even if replays and statistics recording were disabled.
        
        We display each game's winner, seed, and total number of turns played,
		a description of the tournament configuration,
		and the overall win percentages for each personality.
        """
        
		# We first iterate through each game's outcome and print its details
        # since if there are a lot of games and we printed the rest of the summary first,
        # the user would have to scroll back up to see the overall results and configuration details
        # This way, the few lines dedicated to the summary are at the end of the output, making them easier to find
        totalGames = len(outcomes)
        for index, outcome in enumerate(outcomes):
            seed = outcome.seed if outcome.seed is not None else "random"
            if outcome.winnerName is None:
                print(f"Game {index + 1} Winner: None, seed {seed}, {outcome.numberOfTurns} total turns played.")
            else:
                print(f"Game {index + 1} Winner: {outcome.winnerName} ({outcome.winnerColor}), seed {seed}, {outcome.numberOfTurns} total turns played.")

		# A description of the tournament configuration
        description = (
            f"Game played on {self.config.dimension}x{self.config.dimension} grid with "
            f"{self.config.targetLandTiles} land tiles, {len(self.config.personalities)} factions, "
            f"initial province size of {self.config.initialProvinceSize}, and {self.config.seedPicker.describe()}."
        )
        
		# Here we give the overall results for each AI personality, 
        # telling how effective each one was in the tournament
        # and what their name and faction color were if the user wants to look them up in replays or statistics
        print("\nOverall results:")
        print(description)
        for index, personality in enumerate(self.config.personalities):
            color = list(Faction.colorCodesMap.keys())[index % len(list(Faction.colorCodesMap.keys()))]
            print(f"Faction slot {index + 1} was played by the {personality.displayName}, faction color {color}.")
            
        for personality in self.config.personalities:
            wins = winsByPersonality[personality.displayName]
            percentage = (wins / totalGames) * 100 if totalGames > 0 else 0.0
            print(f"{personality.displayName} won {percentage:.1f}% of the time")
