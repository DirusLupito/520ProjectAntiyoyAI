from ai.AIPersonality import AIPersonality
from tournaments.AITournamentConfig import AITournamentConfig
from tournaments.TournamentSeedPicker import TournamentSeedPicker
from tournaments.TournamentRunner import AITournamentRunner
import time

def runSRBTournament() -> None:
    """
    Script for generating the test data for the SRB tournament
    Will match up every SRB AI against every other SRB AI such that
    each AI will play 500 rounds in slot 1 vs their opponent in slot 2,
    then switch and play 500 rounds in slot 2 vs their opponent in slot 1.
    No replays are recorded, only statistics are tracked.
    Each map is randomly generated within the parameters specified:
    - Map dimension: 20x20
    - Target land tiles: 200
    - Initial province size: 10
    - Maximum turns before draw: 1000
    """

    seedPicker = TournamentSeedPicker(seedMode="fullyRandom")


    personalities = [
        AIPersonality("Mark1SRB", "mark1srb"),
        AIPersonality("Mark2SRB", "mark2srb")
    ]
    
    # We set up the initial config object here,
    # though in the next steps we only need to change a few of its fields
    
    # Set up mark 1 in slot 1 vs mark 2 in slot 2
    config = AITournamentConfig(
        personalities=personalities,
        roundCount=500,
        dimension=20,
        targetLandTiles=200,
        initialProvinceSize=10,
        seedPicker=seedPicker,
        recordReplays=False,
        displayGames=False,
        trackStatistics=True,
        # I recommend using a parallel worker count equal to the number 
        # of physical CPU cores on your machine for best performance
        parallelWorkerCount=16,
        maxTurns=1000,
        outputDirectory="Mark1SRB in Slot 1 fighting Mark2SRB in Slot 2",
        printSummary=False,
        summaryFileName="Slot1Mark1SRB_vs_Slot2Mark2SRB_Summary.txt"
    )

    runner = AITournamentRunner(config)
    
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 1 SRB in slot 1 vs Mark 2 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 1 in slot 1 vs mark 3 in slot 2
    personalities = [
        AIPersonality("Mark1SRB", "mark1srb"),
        AIPersonality("Mark3SRB", "mark3srb")
    ]
    
    config.personalities = personalities
    config.outputDirectory = "Mark1SRB in Slot 1 fighting Mark3SRB in Slot 2"
    config.summaryFileName = "Slot1Mark1SRB_vs_Slot3SRB_Summary.txt"
    
    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 1 SRB in slot 1 vs Mark 3 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 1 in slot 1 vs mark 4 in slot 2
    personalities = [
        AIPersonality("Mark1SRB", "mark1srb"),
        AIPersonality("Mark4SRB", "mark4srb")
    ]
    
    config.personalities = personalities
    config.outputDirectory = "Mark1SRB in Slot 1 fighting Mark4SRB in Slot 2"
    config.summaryFileName = "Slot1Mark1SRB_vs_Slot4SRB_Summary.txt"
    
    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 1 SRB in slot 1 vs Mark 4 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 2 in slot 1 vs mark 1 in slot 2
    personalities = [
        AIPersonality("Mark2SRB", "mark2srb"),
        AIPersonality("Mark1SRB", "mark1srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark2SRB in Slot 1 fighting Mark1SRB in Slot 2"
    config.summaryFileName = "Slot1Mark2SRB_vs_Slot1Mark1SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 2 SRB in slot 1 vs Mark 1 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 3 in slot 1 vs mark 1 in slot 2
    personalities = [
        AIPersonality("Mark3SRB", "mark3srb"),
        AIPersonality("Mark1SRB", "mark1srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark3SRB in Slot 1 fighting Mark1SRB in Slot 2"
    config.summaryFileName = "Slot1Mark3SRB_vs_Slot1Mark1SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 3 SRB in slot 1 vs Mark 1 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 4 in slot 1 vs mark 1 in slot 2
    personalities = [
        AIPersonality("Mark4SRB", "mark4srb"),
        AIPersonality("Mark1SRB", "mark1srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark4SRB in Slot 1 fighting Mark1SRB in Slot 2"
    config.summaryFileName = "Slot1Mark4SRB_vs_Slot1Mark1SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 4 SRB in slot 1 vs Mark 1 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 2 in slot 1 vs mark 3 in slot 2
    personalities = [
        AIPersonality("Mark2SRB", "mark2srb"),
        AIPersonality("Mark3SRB", "mark3srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark2SRB in Slot 1 fighting Mark3SRB in Slot 2"
    config.summaryFileName = "Slot1Mark2SRB_vs_Slot1Mark3SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 2 SRB in slot 1 vs Mark 3 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 2 in slot 1 vs mark 4 in slot 2
    personalities = [
        AIPersonality("Mark2SRB", "mark2srb"),
        AIPersonality("Mark4SRB", "mark4srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark2SRB in Slot 1 fighting Mark4SRB in Slot 2"
    config.summaryFileName = "Slot1Mark2SRB_vs_Slot1Mark4SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 2 SRB in slot 1 vs Mark 4 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 3 in slot 1 vs mark 2 in slot 2
    personalities = [
        AIPersonality("Mark3SRB", "mark3srb"),
        AIPersonality("Mark2SRB", "mark2srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark3SRB in Slot 1 fighting Mark2SRB in Slot 2"
    config.summaryFileName = "Slot1Mark3SRB_vs_Slot1Mark2SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 3 SRB in slot 1 vs Mark 2 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 4 in slot 1 vs mark 2 in slot 2
    personalities = [
        AIPersonality("Mark4SRB", "mark4srb"),
        AIPersonality("Mark2SRB", "mark2srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark4SRB in Slot 1 fighting Mark2SRB in Slot 2"
    config.summaryFileName = "Slot1Mark4SRB_vs_Slot1Mark2SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 4 SRB in slot 1 vs Mark 2 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 3 in slot 1 vs mark 4 in slot 2
    personalities = [
        AIPersonality("Mark3SRB", "mark3srb"),
        AIPersonality("Mark4SRB", "mark4srb")
    ]

    config.personalities = personalities
    config.outputDirectory = "Mark3SRB in Slot 1 fighting Mark4SRB in Slot 2"
    config.summaryFileName = "Slot1Mark3SRB_vs_Slot1Mark4SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 3 SRB in slot 1 vs Mark 4 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")
    
    # Set up mark 4 in slot 1 vs mark 3 in slot 2
    personalities = [
        AIPersonality("Mark4SRB", "mark4srb"),
        AIPersonality("Mark3SRB", "mark3srb")
    ]
    
    config.personalities = personalities
    config.outputDirectory = "Mark4SRB in Slot 1 fighting Mark3SRB in Slot 2"
    config.summaryFileName = "Slot1Mark4SRB_vs_Slot1Mark3SRB_Summary.txt"

    runner = AITournamentRunner(config)
    start_time = time.perf_counter()
    runner.runTournament()
    end_time = time.perf_counter()
    print(f"Mark 4 SRB in slot 1 vs Mark 3 SRB in slot 2 tournament completed in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    runSRBTournament()