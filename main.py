# Starting point of the Antiyoy AI project program
from game.Scenario import Scenario

def main():
    """
    Main function to run the Antiyoy AI project.
    Holds the entry point for the program.
    Handles the outermost logic of the turn-based strategy game,
    including the loop for turns and holds the game state data structures.
    """
    print("ASCIIyoy")
    # Invalid map data in reality, but of the right dimension to
    # test the printing of a map (2x5 grid of the integer 0).
    mapData = [[0] * 5 for _ in range(2)]
    scenario = Scenario(name="debug", mapData=mapData)
    scenario.printMap()

if __name__ == "__main__":
    main()
