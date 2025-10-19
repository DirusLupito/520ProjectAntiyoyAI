# Starting point of the Antiyoy AI project program
from game.Scenario import Scenario
from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction

def main():
    """
    Main function to run the Antiyoy AI project.
    Holds the entry point for the program.
    Handles the outermost logic of the turn-based strategy game,
    including the loop for turns and holds the game state data structures.
    """
    print("ASCIIyoy")
    dimension = 10
    targetNumberOfLandTiles = 60
    initialProvinceSize = 2
    faction1 = Faction(name="Faction 1", color="Red")
    faction2 = Faction(name="Faction 2", color="Blue")
    factions = [faction1, faction2]
    randomSeed = 2
    scenario = generateRandomScenario(dimension, targetNumberOfLandTiles, factions, initialProvinceSize, randomSeed)
    scenario.printMap()
    scenario.printMapWithDetails()


if __name__ == "__main__":
    main()
