# Starting point of the Antiyoy AI project program
from game.Scenario import Scenario
from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction
import pdb

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
    scenario.displayMap()
    # Keeps track of all actions taken in the turn for potential undo
    actions = []
    print(f"The faction to play is {scenario.getFactionToPlay().name}, with color {scenario.getFactionToPlay().color}")
    print(f"This faction has {len(scenario.getFactionToPlay().provinces)} province(s).")
    for i, province in enumerate(scenario.getFactionToPlay().provinces):
        print(f"    Province {i+1} has {len(province.tiles)} tiles and {province.resources} resources. Its income per turn is {province.computeIncome()}.")
        print(f"    Available tiles in this province:")
        for tile in province.tiles:
            print(f"        Tile at ({tile.row}, {tile.col}) - Unit: {tile.unit.unitType if tile.unit else 'None'}, Owner: {tile.owner.faction.name if tile.owner else 'None'}")
            
        tileCoord = input("    Enter tile coordinates (row, col): ")
        row, col = map(int, tileCoord.split(","))
        tile = scenario.mapData[row][col]
        print(f"    Tile details - isWater: {tile.isWater}, Owner: {tile.owner.faction.name if tile.owner else 'None'}, Unit: {tile.unit.unitType if tile.unit else 'None'}")
        print(f"    Available units for this province to build on this tile:")
        unitTypes = scenario.getBuildableUnitsOnTile(row, col, province)
        for i, unitType in enumerate(unitTypes):
            print(f"    Item {i+1}: {unitType}")
        itemNumber = int(input("Enter 0 for no unit, or the item number to build that unit: "))
        if itemNumber > 0 and itemNumber <= len(unitTypes):
            selectedUnitType = unitTypes[itemNumber - 1]
            currActionIndex = len(actions)
            actions.extend(scenario.buildUnitOnTile(row, col, selectedUnitType, province))
            latestActions = actions[currActionIndex:]
            for action in latestActions:
                scenario.applyAction(action, province)
            print(f"Built {selectedUnitType} on tile ({row}, {col}).")
        else:
            print("No unit built.")
        print(f"    Province {i+1} has {len(province.tiles)} tiles and {province.resources} resources. Its income per turn is {province.computeIncome()}.")
        numUnitsWhichCanMove = sum(1 for tile in province.tiles if tile.unit and tile.unit.canMove and tile.unit.owner == province.faction)
        print(f"    Province {i+1} has {numUnitsWhichCanMove} unit(s) that can move.")
        scenario.displayMap()
        for _ in range(numUnitsWhichCanMove):
            moveInput = input("    Enter move command as initialRow,initialCol->finalRow,finalCol (or 'done' to finish moves): ")
            if moveInput.lower() == 'done':
                break
            initialPart, finalPart = moveInput.split("->")
            initialRow, initialCol = map(int, initialPart.split(","))
            finalRow, finalCol = map(int, finalPart.split(","))
            currActionIndex = len(actions)
            actions.extend(scenario.moveUnit(initialRow, initialCol, finalRow, finalCol))
            latestActions = actions[currActionIndex:]
            for action in latestActions:
                scenario.applyAction(action, province)
            scenario.displayMap()
            print(f"    Moved unit from ({initialRow}, {initialCol}) to ({finalRow}, {finalCol}).")
        inputUndo = input("    Do you want to undo the last action? (y/n): ")
        if inputUndo.lower() == 'y' and actions:
            print("    Undoing the last action...")
            # undo the actions by applying their inverses in reverse order
            # until hitting an action which is not a consequence of the original action
            # undo that final consequence at the very end
            latestAction = actions[-1] if actions else None
            while latestAction.isDirectConsequenceOfAnotherAction:
                scenario.applyAction(latestAction.invert(), province)
                actions.pop()
                latestAction = actions[-1] if actions else None
            if latestAction:
                scenario.applyAction(latestAction.invert(), province)
                actions.pop()
            print(f"    After undo, Province {i+1} has {len(province.tiles)} tiles and {province.resources} resources. Its income per turn is {province.computeIncome()}.")

    scenario.displayMap()
    scenario.advanceTurn()
    scenario.displayMap()


if __name__ == "__main__":
    main()
