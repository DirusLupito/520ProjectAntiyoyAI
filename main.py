# Starting point of the Antiyoy AI project program
from game.scenarioGenerator import generateRandomScenario
from game.world.factions.Faction import Faction
from game.replays.Replay import Replay
from ai.AIPersonality import AIPersonality
from ai.utils.commonAIUtilityFunctions import getAllMovableUnitTilesInProvince
import pdb

def getIntegerInput(prompt, minValue=None, maxValue=None):
    """Helper function to get valid integer input from the user."""
    while True:
        try:
            value = int(input(prompt))
            if minValue is not None and value < minValue:
                print(f"Value must be at least {minValue}.")
                continue
            if maxValue is not None and value > maxValue:
                print(f"Value must be at most {maxValue}.")
                continue
            return value
        except ValueError:
            print("Please enter a valid integer.")

def promptYesNo(promptText):
    """Helper function to prompt the user for a yes/no response."""
    while True:
        choice = input(promptText).strip().lower()
        if choice in ("y", "yes"):
            return True
        if choice in ("n", "no"):
            return False
        print("Please enter 'y' or 'n'.")


def offerSavedReplayView():
    """
    Helper function which handles both prompting the user to watch a saved replay
    and loading/playing the replay if they choose to do so.
    """
    while True:
        watch = input("Watch a saved replay? (y/n): ").strip().lower()
        if watch in ("n", "no"):
            return
        if watch in ("y", "yes"):
            path = input("Enter replay file path: ").strip()
            try:
                replay = Replay.loadFromFile(path)
                replay.playInteractive()
            except Exception as exc:
                print(f"Failed to play replay: {exc}")
        else:
            print("Please enter 'y' or 'n'.")

def main():
    """
    Main function to run the Antiyoy AI project.
    Holds the entry point for the program.
    Handles the outermost logic of the turn-based strategy game,
    including the loop for turns and holds the game state data structures.
    """
    print("===== ASCIIyoy =====")
    print("An ASCII-based implementation of the Antiyoy strategy game.")

    offerSavedReplayView()
    
    print("\n--- Game Setup ---")
    dimension = getIntegerInput("Enter map dimension (recommended <=10): ", minValue=2)
    
    maxLandTiles = dimension * dimension
    targetNumberOfLandTiles = getIntegerInput(f"Enter target number of land tiles (min 4, max {maxLandTiles}): ",
                                              minValue=4, maxValue=maxLandTiles)
    
    maxFactions = targetNumberOfLandTiles // 2 - 1
    numFactions = getIntegerInput(f"Enter number of factions (max {maxFactions}): ", 
                                   minValue=1, maxValue=maxFactions)
    initialProvinceSize = getIntegerInput("Enter initial province size (recommended 2-6): ", minValue=2, maxValue=maxLandTiles // numFactions)
    
    factions = []
    for i in range(numFactions):
        name = input(f"Enter name for Faction {i+1}: ")
        color = input(f"Enter color for Faction {i+1} (e.g. Red, Blue, Green): ")
        
        playerType = ""
        while playerType not in ["h", "a"]:
            playerType = input(f"Is Faction {i+1} controlled by a (h)uman or (a)i? ").lower()
            if playerType not in ["h", "a"]:
                print("Please enter 'h' for human or 'a' for ai.")
        playerType = "human" if playerType == "h" else "ai"

        aiType = None
        if playerType == "ai":
            while aiType not in AIPersonality.implementedAIs:
                print("Available AI types:")
                for aiKey in AIPersonality.implementedAIs.keys():
                    print(f"  - {aiKey}")
                aiType = input(f"Enter AI type for Faction {i+1}: ").lower()

        factions.append(Faction(name=name, color=color, playerType=playerType, aiType=aiType))
    
    randomSeed = getIntegerInput("Enter random seed (any number): ")
    
    replayMetadata = {
        "dimension": dimension,
        "targetLandTiles": targetNumberOfLandTiles,
        "initialProvinceSize": initialProvinceSize,
        "randomSeed": randomSeed,
        "factions": [
            {
                "name": faction.name,
                "color": faction.color,
                "playerType": faction.playerType,
                "aiType": faction.aiType
            }
            for faction in factions
        ]
    }

    # Generate scenario
    print("\nGenerating map...")
    scenario = generateRandomScenario(dimension, targetNumberOfLandTiles, factions, initialProvinceSize, randomSeed)
    replay = Replay.fromScenario(scenario, metadata=replayMetadata)
    
    # Game loop
    gameOver = False
    while not gameOver:
        # Check win condition
        activeFactions = 0
        for faction in factions:
            if any(province.active for province in faction.provinces):
                activeFactions += 1
        
        if activeFactions <= 1:
            gameOver = True
            break
        
        currentFaction = scenario.getFactionToPlay()
        print(f"\n===== {currentFaction.name}'s Turn ({currentFaction.color}) =====")

        # Handles AI player's turn
        if currentFaction.playerType == "ai":
            scenario.displayMap()
            print(f"{currentFaction.name} (AI) is thinking...")
            debugInput = input("Press Enter to continue, b to break into debugger... ")
            if debugInput.lower() == "b":
                pdb.set_trace()
            
            # Get the AI's chosen actions
            aiFunction = AIPersonality.implementedAIs[currentFaction.aiType]
            aiActions = aiFunction(scenario, currentFaction)
            appliedActions = []
            
            # Apply all actions returned by the AI
            if not aiActions:
                print(f"{currentFaction.name} (AI) chose to do nothing.")
            else:
                print(f"{currentFaction.name} (AI) is performing {len(aiActions)} actions...")
                for action, province in aiActions:
                    try:
                        scenario.applyAction(action, province)
                        appliedActions.append((action, province))
                        # debug
                        # print(f"  - {action.actionType} on province {province.faction.name}")
                    except Exception as e:
                        print(f"AI generated an invalid action, skipping. Error: {e}")
            
            # End AI's turn
            turnAdvanceActions = scenario.advanceTurn()
            turnActionsForReplay = list(appliedActions)
            turnActionsForReplay.extend(turnAdvanceActions)
            replay.recordTurn(scenario, currentFaction, turnActionsForReplay)
            continue # Skip to the next iteration of the main game loop

        # Handles human player's turn
        
        # Display map at the start of turn
        scenario.displayMap()
        
        # Initialize turn variables
        # Track actions and their associated selected province for undo functionality
        # Actions stores a list of tuples of (action, provinceAtTimeOfAction)
        actions = [] 
        selectedProvince = None
        selectedUnit = None
        selectedUnitPosition = None
        turnEnded = False
        
        # Faction's turn loop
        while not turnEnded:
            # Get active provinces
            activeProvinces = [p for p in currentFaction.provinces if p.active]
            if not activeProvinces:
                print("You have no active provinces! Your turn is skipped.")
                turnEnded = True
                continue
                
            # Display province selection if no province selected
            if selectedProvince is None:
                print("\nYour provinces:")
                for i, province in enumerate(activeProvinces):
                    print(f"  {i+1}. Province with {len(province.tiles)} tiles and {province.resources} resources. Income: {province.computeIncome()}")
                print("\nOptions:")
                print("  select <number> - Select a province")
                print("  map - Display the map")
                print("  end - End your turn")
            else:
                # Display selected province info
                provinceIndex = activeProvinces.index(selectedProvince) + 1 if selectedProvince in activeProvinces else "N/A"
                print(f"\nSelected Province {provinceIndex}: {len(selectedProvince.tiles)} tiles, {selectedProvince.resources} resources, income {selectedProvince.computeIncome()}.")   
                
                if selectedUnit:
                    row, col = selectedUnitPosition
                    unitType = scenario.mapData[row][col].unit.unitType if scenario.mapData[row][col].unit else "None"
                    print(f"Selected Unit at ({row}, {col}): {unitType}")
                
                print("\nOptions:")
                print("  select <number> - Select a different province")
                print("  map - Display the map")
                if not selectedUnit:
                    print("  unit <row>,<col> - Select a unit")
                    print("  build <row>,<col> - Check what can be built at location")
                    print("  build <row>,<col> <type> - Build unit type at location")
                    print("  units - List all movable units in selected province")
                else:
                    print("  moves - Show valid moves for selected unit")
                    print("  move <row>,<col> - Move selected unit")
                    print("  deselect - Deselect unit")
                print("  undo - Undo last action")
                print("  end - End your turn")
            
            # Get user command
            cmdUpper = input("\nEnter command: ").strip()
            cmd = cmdUpper.lower()
            
            try:
                if cmd == "map":
                    scenario.displayMap()
                
                elif cmd == "end":
                    turnEnded = True
                
                elif cmd == "undo":
                    if not actions:
                        print("Nothing to undo!")
                    else:
                        # Find the last non-consequence action
                        i = len(actions) - 1
                        while i >= 0 and actions[i][0].isDirectConsequenceOfAnotherAction:
                            i -= 1
                        
                        # Apply inverses in reverse order
                        for j in range(len(actions) - 1, i - 1, -1):
                            # scenario.applyAction(actions[j].invert(), selectedProvince)
                            actionToInvert = actions[j][0]
                            provinceAtTimeOfAction = actions[j][1]
                            scenario.applyAction(actionToInvert.invert(), provinceAtTimeOfAction)
                        
                        # Remove the undone actions
                        actions = actions[:i]
                        print("Action undone.")
                        selectedUnit = None
                        selectedUnitPosition = None
                
                elif cmd.startswith("select "):
                    try:
                        index = int(cmd.split()[1]) - 1
                        if 0 <= index < len(activeProvinces):
                            selectedProvince = activeProvinces[index]
                            selectedUnit = None
                            selectedUnitPosition = None
                            print(f"Selected province with {len(selectedProvince.tiles)} tiles.")
                        else:
                            print("Invalid province number.")
                    except (ValueError, IndexError):
                        print("Invalid selection format. Use 'select <number>'")
                
                elif cmd.startswith("unit ") and selectedProvince:
                    try:
                        coords = cmd.split()[1].split(",")
                        row, col = int(coords[0]), int(coords[1])
                        tile = scenario.mapData[row][col]
                        
                        if tile.owner != selectedProvince:
                            print("That tile doesn't belong to your selected province!")
                            continue
                            
                        if not tile.unit:
                            print("No unit at that location!")
                            continue
                            
                        if not tile.unit.canMove:
                            print("That unit cannot move!")
                            continue
                            
                        selectedUnit = tile.unit
                        selectedUnitPosition = (row, col)
                        print(f"Selected {tile.unit.unitType} at ({row}, {col})")
                    except (ValueError, IndexError):
                        print("Invalid coordinates. Use 'unit <row>,<col>'")
                    except Exception as e:
                        print(f"Error: {str(e)}")
                
                elif cmd == "moves" and selectedUnit:
                    row, col = selectedUnitPosition
                    validMoves = scenario.getAllTilesWithinMovementRangeFiltered(row, col)
                    print("Valid moves:")
                    for moveRow, moveCol in validMoves:
                        if moveRow != row or moveCol != col:  # Don't show current position
                            tile = scenario.mapData[moveRow][moveCol]
                            owner = tile.owner.faction.name if tile.owner else "None"
                            unit = tile.unit.unitType if tile.unit else "None"
                            print(f"  ({moveRow}, {moveCol}) - Owner: {owner}, Unit: {unit}")
                
                elif cmd.startswith("move ") and selectedUnit:
                    try:
                        coords = cmd.split()[1].split(",")
                        targetRow, targetCol = int(coords[0]), int(coords[1])
                        
                        # Get and apply move actions
                        moveActions = scenario.moveUnit(selectedUnitPosition[0], selectedUnitPosition[1], 
                                                      targetRow, targetCol)
                        
                        for action in moveActions:
                            scenario.applyAction(action, selectedProvince)
                        
                        # Add actions to history
                        for action in moveActions:
                            actions.append((action, selectedProvince))
                        
                        print(f"Moved unit from ({selectedUnitPosition[0]}, {selectedUnitPosition[1]}) to ({targetRow}, {targetCol})")
                        
                        # Deselect unit after move
                        selectedUnit = None
                        selectedUnitPosition = None
                    except (ValueError, IndexError):
                        print("Invalid coordinates. Use 'move <row>,<col>'")
                    except Exception as e:
                        print(f"Error: {str(e)}")
                
                elif cmd == "deselect" and selectedUnit:
                    selectedUnit = None
                    selectedUnitPosition = None
                    print("Unit deselected.")

                elif cmd == "units" and selectedProvince:
                    movableUnitTiles = getAllMovableUnitTilesInProvince(selectedProvince)
                    if not movableUnitTiles:
                        print("No movable units in the selected province.")
                    else:
                        print("Movable units in the selected province:")
                        for tile, _ in movableUnitTiles: \
                            print(f"  - {tile.unit.unitType} at ({tile.row}, {tile.col})")
                
                elif cmd.startswith("build ") and selectedProvince:
                    parts = cmd.split()
                    coords = parts[1].split(",")
                    
                    try:
                        row, col = int(coords[0]), int(coords[1])
                        
                        if len(parts) == 2:  # Just checking what can be built
                            buildable = scenario.getBuildableUnitsOnTile(row, col, selectedProvince)
                            if buildable:
                                print(f"Units that can be built at ({row}, {col}):")
                                for i, unitType in enumerate(buildable):
                                    print(f"  {i+1}. {unitType}")
                            else:
                                print(f"No units can be built at ({row}, {col}).")
                        elif len(parts) >= 3:  # Building a unit
                            # Maps shorthand to full unit types
                            # if user used shorthand, convert it
                            shorthandMap = {
                                "s1": "soldierTier1",
                                "s2": "soldierTier2",
                                "s3": "soldierTier3",
                                "s4": "soldierTier4",
                                "fm": "farm",
                                "t1": "tower1",
                                "t2": "tower2",
                            }
                            if parts[2] in shorthandMap:
                                unitType = shorthandMap[parts[2]]
                            else:
                                unitType = cmdUpper.split()[2]  # Preserve original casing for unit type (IMPORTANT)
                            buildable = scenario.getBuildableUnitsOnTile(row, col, selectedProvince)

                            if unitType not in buildable:
                                print(f"Cannot build {unitType} at that location.")
                                continue
                                
                            # Build the unit
                            buildActions = scenario.buildUnitOnTile(row, col, unitType, selectedProvince)
                            for action in buildActions:
                                scenario.applyAction(action, selectedProvince)
                            
                            # Add actions to history
                            for action in buildActions:
                                actions.append((action, selectedProvince))
                            print(f"Built {unitType} at ({row}, {col}).")
                    except (ValueError, IndexError):
                        print("Invalid coordinates. Use 'build <row>,<col>' or 'build <row>,<col> <unitType>'")
                    except Exception as e:
                        print(f"Error: {str(e)}")
                
                else:
                    print("Invalid command.")
                
            except Exception as e:
                print(f"Error: {str(e)}")
        
        # End of turn - advance to next player and apply turn advancement actions
        turnAdvanceActions = scenario.advanceTurn()
        turnActionsForReplay = list(actions)
        turnActionsForReplay.extend(turnAdvanceActions)
        replay.recordTurn(scenario, currentFaction, turnActionsForReplay)

    # Game over
    print("\n===== Game Over =====")
    
    # Find winner if there is one
    winner = None
    for faction in factions:
        if any(province.active for province in faction.provinces):
            winner = faction
            break
    
    if winner:
        print(f"The winner is: {winner.name} ({winner.color})!")
    else:
        print("The game ended with no active provinces remaining.")
    
    # Final map display
    scenario.displayMap()

    if replay.hasTurns() and promptYesNo("Watch the replay of this game now? (y/n): "):
        try:
            replay.playInteractive()
        except Exception as exc:
            print(f"Failed to play replay: {exc}")

    if promptYesNo("Save this game's replay to a file? (y/n): "):
        path = input("Enter file path to save replay: ").strip()
        try:
            replay.saveToFile(path)
            print(f"Replay saved to {path} with file extension .ayrf.")
        except Exception as exc:
            print(f"Failed to save replay: {exc}")

if __name__ == "__main__":
    main()
