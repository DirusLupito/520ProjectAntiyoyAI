# Sample script for running a Mark1SRB vs Mark2SRB tournament.
# Feel free to modify this script to test different configurations.

from ai.AIPersonality import AIPersonality
from tournaments.AITournamentConfig import AITournamentConfig
from tournaments.TournamentSeedPicker import TournamentSeedPicker
from tournaments.TournamentRunner import AITournamentRunner
import time

def runSampleTournament() -> None:
    """
    Creates a simple configuration and runs a short AI tournament
    between the Mark1SRB and Mark2SRB personalities on a 20x20 map
    over 50 rounds with 200 land tiles on each map, each province starting
    with 50 tiles, and a fully random seed picking strategy so every
    game played in the tournament should be on a different map.
    Replays and statistics tracking are enabled.
    """

    # When setting up your own tournament,
    # it is fine to have duplicate personalities in the list
    # This will just result in for example a mark2srb vs mark2srb 
    # or mark2srb vs mark1srb vs mark2srb game being played
    # Just try to give them unique names so you can tell them apart in the results
    personalities = [
        AIPersonality("Mark1SRB", "mark1srb"),
        AIPersonality("Mark2SRB", "mark2srb")
    ]

    # Copied from the TournamentSeedPicker documentation
    # The seed mode can be one of the following:
    # - "fixed": All games use the same fixed seed. For instance, if fixedSeed=2, all games use seed 2.
    # - "sequential": Seeds are taken in order from a provided list. If there are more games than seeds,
    #   the list is cycled through as many times as needed. For instance, if seedList=[1,2,3] and there are 5 games,
    #   the seed for game 1 is 1, game 2 is 2, game 3 is 3, game 4 is 1, and game 5 is 2.
    # - "randomFromPool": Seeds are randomly chosen from a provided list of seeds. If the list is empty but randomPoolSize > 0,
    #   a pool of random seeds is generated to choose from. For instance, if seedList=[10,20,30], each game's seed is randomly picked from these three values.
    #   So if there are 4 games, possible seeds could be [20,10,30,20]. If seedList=[] and randomPoolSize=5,
    #   a pool of 5 random seeds is generated and each game's seed is randomly picked from that pool.
    # - "fullyRandom": Each game uses a completely random seed, meaning no specific seed is assigned and scenarioGenerator.generateRandomScenario
    #   will be called with randomSeed=None.
    seedPicker = TournamentSeedPicker(seedMode="fullyRandom")

    # personalities (List[AIPersonality]): The AI personalities that will compete in the tournament.
    # roundCount (int): The number of rounds to be played in the tournament.
    # dimension (int): The width and height of the square map to be used for each game.
    # targetLandTiles (int): The target number of land tiles for the map.
    # initialProvinceSize (int): The initial size of each faction's starting province.
    # seedPicker (TournamentSeedPicker): The seed picking strategy to use for each game.
    # recordReplays (bool): Whether to record replays of each game. Defaults to False.
    # displayGames (bool): Whether to display each game as it is played. Defaults to False.
    # trackStatistics (bool): Whether to track detailed statistics for each game. Defaults to False.
    # parallelWorkerCount (int): The number of parallel workers to use for running games. Defaults to 1.
    # If parallelWorkerCount > 1, games will be run in parallel using multiple processes. Displaying games is not supported in parallel mode.
    config = AITournamentConfig(
        personalities=personalities,
        roundCount=50,
        dimension=20,
        targetLandTiles=200,
        initialProvinceSize=50,
        seedPicker=seedPicker,
        recordReplays=True,
        displayGames=False,
        trackStatistics=True,
        # I recommend using a parallel worker count equal to the number 
        # of physical CPU cores on your machine for best performance
        parallelWorkerCount=4,
        # If two AIs haven't won in this many turns, declare the game a draw
        maxTurns=1000
    )

    # You must instantiate the runner with a config object
    runner = AITournamentRunner(config)

    # To actually run the tournament, just call runTournament()
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Tournament completed in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    runSampleTournament()
