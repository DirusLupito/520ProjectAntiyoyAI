from typing import List
from ai.AIPersonality import AIPersonality
from tournaments.TournamentSeedPicker import TournamentSeedPicker

class AITournamentConfig:
    """
    Holds all configuration required to run an AI tournament.
    
    A tournament configuration currently includes:
    - The AI personalities that will be competing
    - The number of rounds to be played
    - The map dimension, target land tiles, and initial province size
    - The seed picking strategy to use
    - Whether to record replays, display games, and track statistics
    - How many workers should run games in parallel
    - The maximum number of turns before a game is declared a draw
    - The name of the output directory for tournament results
    - A boolean telling whether or not the tournament summary will be printed to console
    """

    def __init__(
        self,
        personalities: List[AIPersonality],
        roundCount: int,
        dimension: int,
        targetLandTiles: int,
        initialProvinceSize: int,
        seedPicker: TournamentSeedPicker,
        recordReplays: bool = False,
        displayGames: bool = False,
        trackStatistics: bool = False,
        parallelWorkerCount: int = 1,
        maxTurns: int = 0,
        outputDirectory: str = None,
        printSummary: bool = True,
        summaryFileName: str = None
    ) -> None:
        """
        Initializes a new AITournamentConfig with the given parameters.

        Args:
            personalities (List[AIPersonality]): The AI personalities that will compete in the tournament.
            roundCount (int): The number of rounds to be played in the tournament.
            dimension (int): The width and height of the square map to be used for each game.
            targetLandTiles (int): The target number of land tiles for the map.
            initialProvinceSize (int): The initial size of each faction's starting province.
            seedPicker (TournamentSeedPicker): The seed picking strategy to use for each game.
            recordReplays (bool): Whether to record replays of each game. Defaults to False.
            displayGames (bool): Whether to display each game as it is played. Defaults to False.
            trackStatistics (bool): Whether to track detailed statistics for each game. Defaults to False.
            parallelWorkerCount (int): Number of workers that should play games in parallel. Defaults to 1.
            maxTurns (int): The maximum number of turns before a game is declared a draw. Defaults to 0 (no limit).
            outputDirectory (str): The name of the output directory for tournament results. Defaults to None
                which will use a timestamp-based directory name.
            printSummary (bool): Whether to print the tournament summary to console. Defaults to True.
            summaryFileName (str): The name of the file that the tournament summary will be saved to.
                Defaults to None which will cause no file to be created.
        """

        if roundCount <= 0:
            raise ValueError("Round count must be positive.")
        
        if len(personalities) < 2:
            raise ValueError("At least two personalities are required for a tournament.")
        
        if parallelWorkerCount <= 0:
            raise ValueError("Parallel worker count must be at least 1.")
        
        if parallelWorkerCount > 1 and displayGames:
            raise ValueError("Displaying games is not supported when using multiple parallel workers.")
        
        self.personalities = personalities
        self.roundCount = roundCount
        self.dimension = dimension
        self.targetLandTiles = targetLandTiles
        self.initialProvinceSize = initialProvinceSize
        self.seedPicker = seedPicker
        self.recordReplays = recordReplays
        self.displayGames = displayGames
        self.trackStatistics = trackStatistics
        self.parallelWorkerCount = parallelWorkerCount
        self.maxTurns = maxTurns
        self.outputDirectory = outputDirectory
        self.printSummary = printSummary
        self.summaryFileName = summaryFileName