import time

from ai.AIPersonality import AIPersonality
from tournaments.AITournamentConfig import AITournamentConfig
from tournaments.TournamentRunner import AITournamentRunner
from tournaments.TournamentSeedPicker import TournamentSeedPicker


def buildSummaryFilename(slot1Name: str, slot2Name: str) -> str:
    """Create a summary filename using the two display names without whitespace."""

    cleanSlot1 = slot1Name.replace(" ", "")
    cleanSlot2 = slot2Name.replace(" ", "")
    return f"Slot1{cleanSlot1}_vs_Slot2{cleanSlot2}_Summary.txt"


def runMinimaxTournament() -> None:
    """
    Script for generating the test data for the minimax related tournament
    Will match up every AI against minimax such that
    each AI will play 50 rounds in slot 1 vs minimax in slot 2,
    then switch and play 50 rounds in slot 2 vs minimax in slot 1.
    No replays are recorded, only statistics are tracked.
    Each map is randomly generated within the parameters specified:
    - Map dimension: 4x4
    - Target land tiles: 16
    - Initial province size: 4
    - Maximum turns before draw: 1000
    """

    seedPicker = TournamentSeedPicker(seedMode="fullyRandom")

    # Shared configuration parameters for every matchup we run.
    baseTournamentArgs = {
        "roundCount": 50,
        "dimension": 4,
        "targetLandTiles": 16,
        "initialProvinceSize": 4,
        "seedPicker": seedPicker,
        "recordReplays": False,
        "displayGames": False,
        "trackStatistics": True,
        "parallelWorkerCount": 4,
        "maxTurns": 1000,
        "printSummary": False,
    }

    matchups = [
        ("Mark1SRB", "mark1srb", "Minimax", "minimax"),
        ("Minimax", "minimax", "Mark1SRB", "mark1srb"),
        ("Mark2SRB", "mark2srb", "Minimax", "minimax"),
        ("Minimax", "minimax", "Mark2SRB", "mark2srb"),
        ("Mark3SRB", "mark3srb", "Minimax", "minimax"),
        ("Minimax", "minimax", "Mark3SRB", "mark3srb"),
        ("Mark4SRB", "mark4srb", "Minimax", "minimax"),
        ("Minimax", "minimax", "Mark4SRB", "mark4srb"),
        ("Minimax", "minimax", "PPO", "ppo"),
        ("PPO", "ppo", "Minimax", "minimax"),
    ]

    for slot1Name, slot1Type, slot2Name, slot2Type in matchups:
        personalities = [
            AIPersonality(slot1Name, slot1Type),
            AIPersonality(slot2Name, slot2Type),
        ]

        config = AITournamentConfig(
            personalities=personalities,
            outputDirectory=f"{slot1Name} in Slot 1 fighting {slot2Name} in Slot 2",
            summaryFileName=buildSummaryFilename(slot1Name, slot2Name),
            **baseTournamentArgs,
        )

        runner = AITournamentRunner(config)
        startTime = time.perf_counter()
        runner.runTournament()
        endTime = time.perf_counter()
        elapsed = endTime - startTime

        print(f"{slot1Name} in slot 1 vs {slot2Name} in slot 2 tournament completed in {elapsed:.2f} seconds.")


if __name__ == "__main__":
    runMinimaxTournament()
