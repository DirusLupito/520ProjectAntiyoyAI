import json
import pdb
from typing import Any, Dict, List, Optional, Tuple

from game.Action import Action
from game.Scenario import Scenario
from game.world.HexTile import HexTile
from game.world.factions.Faction import Faction
from game.world.factions.Province import Province
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from game.world.units.Unit import Unit


class Replay:
    """
    Represents a recorded replay of a game scenario, 
    including the initial state and a sequence of turns represented by
    actions taken by the various factions in the game.

    A replay can be saved/loaded from a JSON file format,
    though replays are specifically saved in files with the extension ".ayrf".
    The name of the file they're loaded from doesn't matter so long as the contents
    are valid JSON representing a replay.

    A replay has the following structure:
    - metadata: Optional dictionary containing metadata about the replay.
                This will represent essentially all the information used
                to generate the map, including details about the dimensions of the map,
                how many land tiles there were, the random seed used to generate
                the scenario, and the factions.

    - initialState: Dictionary capturing the initial state of the scenario.
                     This holds the name of the scenario, information representing
                     every individual tile on the map (including ownership and units),
                     and details about every single province in the scenario
                     including an ID for it and its faction, its initial resources,
                     whether it is initially active, and the indices of the tiles
                     that belong to it.

    - turns: List of turn entries, each containing the faction index and a list of actions taken during that turn.

    - _factionIndex: Internal mapping of Faction objects to their indices.

    - _provinceIds: Internal mapping of Province objects to unique IDs.
    
    - _provinceCounter: Counter to assign unique IDs to provinces. Ensures that
                         each province gets a unique identifier so that it is 
                         easy to consistently reference them in actions, especially
                         when loading a replay from a file and reconstructing the scenario.

    - _recording: Boolean flag indicating whether the replay is currently recording new turns.
                  This last flag is used to prevent recording on loaded replays.
    """

    def __init__(self, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize a new Replay instance.

        Args:
            metadata (Optional[Dict[str, Any]]): Optional metadata for the replay.
        """
        self.metadata: Dict[str, Any] = metadata or {}
        self.initialState: Optional[Dict[str, Any]] = None
        self.turns: List[Dict[str, Any]] = []
        self._factionIndex: Dict[Faction, int] = {}
        self._provinceIds: Dict[Province, int] = {}
        self._provinceCounter: int = 0
        self._recording: bool = True

    @classmethod
    def fromScenario(cls, scenario: Scenario, metadata: Optional[Dict[str, Any]] = None) -> "Replay":
        """
        Creates a Replay instance from a given Scenario.
        Should be used when starting a new recording of a scenario.

        Args:
            scenario (Scenario): The scenario to record.
            metadata (Optional[Dict[str, Any]]): Optional metadata for the replay.

        Returns:
            Replay: A new Replay instance initialized with the scenario's state.
        """
        replay = cls(metadata)
        replay._prepareFactionIndex(scenario)
        replay.initialState = replay._serializeScenario(scenario)
        return replay

    @classmethod
    def loadFromFile(cls, path: str) -> "Replay":
        """
        Loads a Replay instance from a JSON file.
        Will first try to open the file at the given path,
        then if it can't find it, will try appending ".ayrf" to the path
        and try again.

        Args:
            path (str): The file path to load the replay from.

        Raises:
            FileNotFoundError: If the file does not exist.

        Returns:
            Replay: The loaded Replay instance.
        """

        # First try to open the file at the given path
        try:
            with open(path, "r") as handle:
                # Parse the JSON content into a dictionary
                data = json.load(handle)
        except FileNotFoundError:
            # If the given path didn't work and it doesn't already end with .ayrf,
            # try appending .ayrf and loading again
            if not path.endswith(".ayrf"):
                # Error will be raised here if this also fails
                return cls.loadFromFile(f"{path}.ayrf")
            else:
                # Re-raise the original error
                # if appending .ayrf didn't help
                # (or if the original path already ended with .ayrf)
                raise

        # No error checking, we assume the file is valid
        # and we want to error out if it isn't
        replay = cls(data.get("metadata"))
        replay.initialState = data.get("initialState")
        replay.turns = data.get("turns", [])

        # Ensure that recording is disabled for loaded replays
        replay._recording = False
        return replay

    def saveToFile(self, path: str) -> None:
        """
        Saves the replay to a JSON file, appending .ayrf extension.
        The path should either just be a name like "replay1" 
        or a path like "saves/replay1". 
        
        If the provided path does not end with ".ayrf", it will be appended automatically.

        Args:
            path (str): The file path to save the replay to.

        Raises:
            ValueError: If the replay has no initial state to save.
        """
        path = path if path.endswith(".ayrf") else f"{path}.ayrf"

        if self.initialState is None:
            raise ValueError("Replay has no initial state")
        
        payload = {
            "metadata": self.metadata,
            "initialState": self.initialState,
            "turns": self.turns,
        }

        with open(path, "w") as handle:
            # Less indent makes for smaller files
            json.dump(payload, handle, indent=1)

    def recordTurn(self, scenario: Scenario, faction: Faction, actions: List[Tuple[Action, Optional[Province]]]) -> None:
        """
        Records a turn taken by a faction in a given scenario,
        by serializing the actions taken during that turn.

        This should be called at the end of a faction's turn,
        after all actions have been applied to the scenario,
        every time a faction finishes their turn.
        No undone actions should be included, though it shouldn't
        break anything if they are, it'll just be a waste of space
        to store both an action and its subsequent inverse.

        Args:
            scenario (Scenario): The scenario in which the turn was taken.
            faction (Faction): The faction that took the turn.
            actions (List[Tuple[Action, Optional[Province]]]): List of tuples, each containing an Action and the Province that performed it (if any).

        Raises:
            RuntimeError: If attempting to record on a loaded replay or if the initial state has not been captured.
        """

        if not self._recording:
            raise RuntimeError("Cannot record on a loaded replay")
        
        if self.initialState is None:
            raise RuntimeError("Initial state must be captured before recording turns")
        
        turnEntry = {
            "factionIndex": self._factionIndex[faction],
            "actions": []
        }

        # Iterate over every pair of (action, province) and serialize them
        for action, province in actions:
            serialized = self._serializeAction(action)
            serialized["performedByProvinceId"] = self._ensureProvinceId(province)
            turnEntry["actions"].append(serialized)

        self.turns.append(turnEntry)

    def hasTurns(self) -> bool:
        """
        Returns True if the replay has any recorded turns.
        Used to check if we should even bother prompting
        the user to step through the replay of the game
        they just played, or save said replay.

        Returns:
            bool: True if there are recorded turns, False otherwise.
        """

        return bool(self.turns)

    def playInteractive(self) -> None:
        """
        Plays back the replay interactively, very similar
        to if the game were played by only AI players whose
        personality is just to play the exact same moves as recorded
        in the replay.

        Can be debugged after each turn in case the application
        of some action sequence does not yield the expected result.

        Raises:
            ValueError: If the replay is missing the initial state.
        """

        # First we need to figure out what the initial state is
        # and how to map province IDs to actual Province objects
        scenario, provinceMap = self._buildPlaybackContext()
        if scenario is None:
            raise ValueError("Replay missing initial state")
        
        print("\n=== Replay Start ===")
        scenario.displayMap()
        if not self.turns:
            # If somehow an empty replay got here, we just gracefully exit
            print("No turns were recorded.")
            print("=== Replay Finished ===\n")
            return
        
        # User can also immediately enter debugger before starting
        # the playback
        debugInput = input("Press Enter to begin stepping through turns, or b to enter debugger: ").strip().lower()
        if debugInput == "b":
            pdb.set_trace()

        # Now we step through each faction's full turn (no stepping through
        # individual actions because that seems unnecessary except for debugging,
        # and in that case you should just notice the bug, restart the replay,
        # and then enter the debugger right before the turn you want to debug).
        for turnIndex, turn in enumerate(self.turns, start=1):

            faction = scenario.factions[turn["factionIndex"]]
            scenario.indexOfFactionToPlay = turn["factionIndex"]

            # Turn index helps for debugging so you can know when you're
            # coming up on a specific turn that caused issues
            print(f"\n--- Turn {turnIndex}: {faction.name} ({faction.color}) ---")
            if not turn["actions"]:
                print("No actions this turn.")

            for actionEntry in turn["actions"]:
                # Actually apply the faction's action to the scenario
                performedBy = provinceMap.get(actionEntry.get("performedByProvinceId"))
                actionObj = self._deserializeAction(actionEntry, scenario, provinceMap)
                scenario.applyAction(actionObj, performedBy)

            # We display the map at the end of each turn rather than before because it looks better this way
            scenario.displayMap()
            proceed = input("Press Enter for next turn, b to enter debugger, or q to quit replay: ").strip().lower()

            if proceed == "b":
                pdb.set_trace()

            if proceed == "q":
                print("Replay stopped early by user.")
                print("=== Replay Finished ===\n")
                return
            
            # Mimics the turn advancement in the original game
            # Since update after turn and update before turn methods
            # return Actions which are recorded, it is not necessary
            # to call them here, just to advance the turn index
            # which would otherwise be done in scenario.advanceTurn()
            if scenario.factions:
                scenario.indexOfFactionToPlay = (turn["factionIndex"] + 1) % len(scenario.factions)

        print("\n=== Replay Finished ===\n")

    def _prepareFactionIndex(self, scenario: Scenario) -> None:
        """
        Walks through the factions in the scenario
        and builds a mapping of Faction objects to their indices
        by just enumerating them in order.

        Args:
            scenario (Scenario): The scenario to prepare the faction index for.
        """
        self._factionIndex = {}
        for idx, faction in enumerate(scenario.factions):
            self._factionIndex[faction] = idx

    def _serializeScenario(self, scenario: Scenario) -> Dict[str, Any]:
        """
        Serializes the given scenario into a dictionary format suitable for saving as
        a part of the replay's initial state in JSON.

        Args:
            scenario (Scenario): The scenario to serialize.

        Returns:
            Dict[str, Any]: The serialized scenario data.
        """
        self._provinceIds = {}
        self._provinceCounter = 0
        # We first build what amounts to a block of
        # text representing all the provinces in the scenario
        provincesBlock: List[Dict[str, Any]] = []
        for faction in scenario.factions:
            for province in faction.provinces:
                # Make sure every province has a unique ID
                # or gets a new one assigned if we haven't seen it yet
                pid = self._ensureProvinceId(province)
                
                # We sort the tile coordinates to ensure consistent ordering 
                # when turning the province tiles into JSON text
                tileCoords = sorted({(tile.row, tile.col) for tile in province.tiles})

                # Represents the actual province entry
                provincesBlock.append({
                    "id": pid,
                    "factionIndex": self._factionIndex[province.faction],
                    "resources": province.resources,
                    "active": province.active,
                    "tiles": [[r, c] for r, c in tileCoords]
                })
        # Next we work on the map block
        # representing every tile on the map
        # as JSON
        mapBlock: List[List[Dict[str, Any]]] = []
        for row in scenario.mapData:
            rowBlock: List[Dict[str, Any]] = []
            for tile in row:

                # We don't need to serialize neighbors
                # or coordinates since those can be inferred
                # from the position in the map array
                rowBlock.append({
                    "isWater": tile.isWater,
                    "ownerProvinceId": self._provinceIds.get(tile.owner),
                    "unit": self._serializeUnit(tile.unit)
                })

            mapBlock.append(rowBlock)

        # The final piece of information not already captured
        # is the name, color, and player/AI type of each faction
        # A human player should have an aiType of None
        factionsBlock = []
        for faction in scenario.factions:
            factionsBlock.append({
                "name": faction.name,
                "color": faction.color,
                "playerType": faction.playerType,
                "aiType": faction.aiType
            })

        return {
            "name": scenario.name,
            "indexOfFactionToPlay": scenario.indexOfFactionToPlay,
            "map": mapBlock,
            "factions": factionsBlock,
            "provinces": provincesBlock
        }

    def _serializeUnit(self, unit: Optional[Unit]) -> Optional[Dict[str, Any]]:
        """
        Serializes a unit into a dictionary format suitable for JSON serialization.

        Args:
            unit (Optional[Unit]): The unit to serialize.

        Returns:
            Optional[Dict[str, Any]]: The serialized unit data or None if the unit is None.
        """

        if unit is None:
            return None
        
        ownerIndex = None
        if unit.owner is not None:
            ownerIndex = self._factionIndex.get(unit.owner)

        data: Dict[str, Any] = {
            "unitType": unit.unitType,
            "canMove": unit.canMove,
            "ownerFactionIndex": ownerIndex
        }
        
        # Handle soldiers
        if isinstance(unit, Soldier):
            data["kind"] = "soldier"
            data["tier"] = unit.tier
        # Handle structures
        elif isinstance(unit, Structure):
            data["kind"] = "structure"
        # Handle trees
        elif isinstance(unit, Tree):
            data["kind"] = "tree"
            data["isGravestone"] = unit.unitType == "gravestone"
        # If its none of the above, we will just call it unknown
        # and serialize some fundamental stats which any unit should have
        else:
            data["kind"] = "unknown"
            data["attackPower"] = unit.attackPower
            data["defensePower"] = unit.defensePower
            data["upkeep"] = unit.upkeep
            data["cost"] = unit.cost

        return data

    def _deserializeUnit(self, data: Optional[Dict[str, Any]], factions: List[Faction]) -> Optional[Unit]:
        """
        Takes a serialized unit dictionary and reconstructs the corresponding Unit object.

        Args:
            data (Optional[Dict[str, Any]]): The serialized unit data.
            factions (List[Faction]): List of factions to resolve ownership.
        
        Returns:
            Optional[Unit]: The deserialized Unit object or None if data is None.
        """

        if data is None:
            return None
        
        owner = None
        ownerIndex = data.get("ownerFactionIndex")
        if ownerIndex is not None and 0 <= ownerIndex < len(factions):
            owner = factions[ownerIndex]

        # What "kind" of unit is this? Soldier? Structure? Tree? Unknown?
        kind = data.get("kind")
        if kind == "soldier":
            tier = data.get("tier", 1)
            unit = Soldier(tier=tier, owner=owner)
        elif kind == "structure":
            unit = Structure(structureType=data.get("unitType"), owner=owner)
        elif kind == "tree":
            isGravestone = data.get("isGravestone", False)
            unit = Tree(isGravestone=isGravestone, owner=owner)
        # In the case that the unit is some unknown type,
        # we should have stored some basic stats about it
        # We'll also say it can't move, and if any action
        # does move it, that should already be recorded in
        # the replay, and so we don't need to care about 
        # that here
        # If for whatever reason any of the stats are missing,
        # we just default to 0
        else:
            unit = Unit(
                unitType=data.get("unitType"),
                attackPower=data.get("attackPower", 0),
                defensePower=data.get("defensePower", 0),
                upkeep=data.get("upkeep", 0),
                cost=data.get("cost", 0),
                canMove=data.get("canMove", False),
                owner=owner
            )
        # In case the canMove flag is saved, we will
        # override whatever the constructor defaulted to
        unit.canMove = data.get("canMove", unit.canMove)
        return unit

    def _ensureProvinceId(self, province: Optional[Province]) -> Optional[int]:
        """
        Ensures that the given province has a unique ID assigned,
        even if it is encountered for the first time or if we've seen it before.

        Args:
            province (Optional[Province]): The province to ensure an ID for.

        Returns:
            Optional[int]: The unique ID assigned to the province.
        """

        if province is None:
            return None
        
        # By tracking how many provinces we've seen so far,
        # we can just assign new IDS by adding 1 to the biggest
        # one we've seen so far which will guarantee uniqueness.
        if province not in self._provinceIds:
            self._provinceCounter += 1
            self._provinceIds[province] = self._provinceCounter

        return self._provinceIds[province]

    def _serializeTileState(self, state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Serializes the state of a tile, including its unit and owner province ID.

        Args:
            state (Optional[Dict[str, Any]]): The state of the tile to serialize.

        Returns:
            Optional[Dict[str, Any]]: The serialized state of the tile.
        """

        if state is None:
            return None
        
        result: Dict[str, Any] = {}

        # We already have a function for serializing units
        # so we just use that here
        if "unit" in state:
            result["unit"] = self._serializeUnit(state["unit"])

        if "owner" in state:
            result["ownerProvinceId"] = self._ensureProvinceId(state["owner"])

        return result

    def _serializeAction(self, action: Action) -> Dict[str, Any]:
        """
        Takes an Action object and serializes it into a dictionary format
        to be saved in the replay JSON.

        Args:
            action (Action): The action to serialize.

        Raises:
            ValueError: If the action type is not supported.

        Returns:
            Dict[str, Any]: The serialized action.
        """

        # All actions have a type and whether they are a direct consequence
        # of another action
        base = {
            "type": action.actionType,
            "isConsequence": getattr(action, "isDirectConsequenceOfAnotherAction", False)
        }

        # Here, we handle specific action types and serialize
        # their data accordingly
        # See documentation of Action class for details
        if action.actionType == "moveUnit":
            unitMoved = action.data.get("unitMoved")
            sameUnit = unitMoved is action.data.get("resultantFinalHexState", {}).get("unit")
            base["data"] = {
                # Default to (0,0) if coordinates aren't provided for some reason
                # helps with debugging since we can just look for oddities
                # at (0,0) if something goes wrong with unit movement
                "initial": list(action.data.get("initialHexCoordinates", (0, 0))),
                "final": list(action.data.get("finalHexCoordinates", (0, 0))),
                "resultantInitial": self._serializeTileState(action.data.get("resultantInitialHexState")),
                "resultantFinal": self._serializeTileState(action.data.get("resultantFinalHexState")),
                "unitMovedMatchesResultantFinal": sameUnit,
                "incomeFromMove": action.data.get("incomeFromMove", 0)
            }
        elif action.actionType == "tileChange":
            base["data"] = {
                # Similar to above, default hexCoordinates to (0,0) if missing
                # to help with spotting issues
                "coordinates": list(action.data.get("hexCoordinates", (0, 0))),
                "newTileState": self._serializeTileState(action.data.get("newTileState")),
                "costOfAction": action.data.get("costOfAction", 0)
            }
        elif action.actionType == "provinceCreate":
            province = action.data.get("province")
            faction = action.data.get("faction")
            pid = self._ensureProvinceId(province)
            initialTiles = action.data.get("initialTiles")
            if not initialTiles and province is not None:
                initialTiles = province.tiles
            tileCoords = []
            if initialTiles:
                tileCoords = [[tile.row, tile.col] for tile in initialTiles]
            base["data"] = {
                "provinceId": pid,
                "factionIndex": self._factionIndex[faction],
                "resources": province.resources if province else 0,
                "active": province.active if province else False,
                "initialTiles": tileCoords
            }
        elif action.actionType == "provinceDelete":
            province = action.data.get("province")
            pid = self._ensureProvinceId(province)
            provinceState = action.data.get("provinceState")
            statePayload = None
            if provinceState:
                statePayload = {
                    "resources": provinceState.get("resources", 0),
                    "active": provinceState.get("active", False),
                    "tiles": [[tile.row, tile.col] for tile in provinceState.get("tiles", [])]
                }
            base["data"] = {
                "provinceId": pid,
                "factionIndex": self._factionIndex[action.data.get("faction")],
                "provinceState": statePayload
            }
        elif action.actionType == "provinceResourceChange":
            province = action.data.get("province")
            pid = self._ensureProvinceId(province)
            base["data"] = {
                "provinceId": pid,
                "previousResources": action.data.get("previousResources", 0),
                "newResources": action.data.get("newResources", 0)
            }
        elif action.actionType == "provinceActivationChange":
            province = action.data.get("province")
            pid = self._ensureProvinceId(province)
            base["data"] = {
                "provinceId": pid,
                "previousActiveState": action.data.get("previousActiveState", False),
                "newActiveState": action.data.get("newActiveState", False)
            }
        else:
            raise ValueError(f"Unsupported action type for replay serialization: {action.actionType}")
        return base

    def _buildPlaybackContext(self) -> Tuple[Optional[Scenario], Dict[int, Province]]:
        """
        Reconstructs the initial scenario and a mapping of province IDs to Province objects
        from the replay's initial state which should come from the saved JSON data being loaded
        in, or alternatively from the initial state captured when starting a replay immediately
        after a game finished with everything still in memory.

        The prototype of Scenario's __init__ is as follows:
        __init__(self, name, mapData=None, factions=None, indexOfFactionToPlay=0):
        So we need:
        - name: from initialState["name"]
        - mapData: 2D list of HexTile objects reconstructed from initialState["map"]
        - factions: list of Faction objects reconstructed from initialState["factions"]
        - indexOfFactionToPlay: from initialState["indexOfFactionToPlay"]

        Of these, the mapData and factions are the most complex to reconstruct,
        and factions itself needs to be built by first reconstructing the 
        constituent Provinces belonging to each faction.
        mapData's HexTiles also need to have their owner and unit fields
        properly set based on the provinces and units saved in the initial state.

        Returns:
            Tuple[Optional[Scenario], Dict[int, Province]]: The reconstructed Scenario and province ID mapping.
        """
        
        if self.initialState is None:
            return None, {}
        
        factions = []
        
        # Let's first construct a list of all factions
        # for the scenario we're reconstructing
        for entry in self.initialState.get("factions", []):
            factions.append(Faction(name=entry.get("name"), color=entry.get("color"), playerType=entry.get("playerType"), aiType=entry.get("aiType")))
            
        # Next we build the map of HexTiles
        # as the map existed in the initial state
        # of the scenario
        # This will become mapData for our reconstructed Scenario
        mapRows: List[List[HexTile]] = []
        for rowIndex, row in enumerate(self.initialState.get("map", [])):
            
            # For every row, for every column
            # we initialize a HexTile object
            # and determine if it's water or land
            # based on our saved data from the initial state
            mapRow: List[HexTile] = []
            for colIndex, tileData in enumerate(row):
                tile = HexTile(rowIndex, colIndex, isWater=tileData.get("isWater", False))
                mapRow.append(tile)
                
            mapRows.append(mapRow)

        # Now we need to set up the neighbors field for every tile
        # to complete the mapData structure
        self._setupNeighborsForMap(mapRows)

        # Next, we build the Province datastructure
        # that our initial Scenario needs to be built
        provinceMap: Dict[int, Province] = {}
        for provinceData in self.initialState.get("provinces", []):
            factionIndex = provinceData.get("factionIndex", 0)
            faction = factions[factionIndex]
            province = Province(tiles=[], resources=provinceData.get("resources", 0), faction=faction)
            province.active = provinceData.get("active", False)
            faction.provinces.append(province)
            provinceMap[provinceData["id"]] = province

        # Now that we have our provinces, we can fill in the owner
        # field for our mapData tiles, as well as the unit field
        # for those same tiles.
        for rowIndex, row in enumerate(self.initialState.get("map", [])):
            for colIndex, tileData in enumerate(row):
                tile = mapRows[rowIndex][colIndex]
                ownerId = tileData.get("ownerProvinceId")
                owner = provinceMap.get(ownerId)
                if owner is not None and tile not in owner.tiles:
                    owner.tiles.append(tile)
                    tile.owner = owner
                unit = self._deserializeUnit(tileData.get("unit"), factions)
                tile.unit = unit

        # Finally, we have all the pieces we need to construct our initial Scenario
        scenario = Scenario(self.initialState.get("name", "Replay"), mapRows, factions, self.initialState.get("indexOfFactionToPlay", 0))

        return scenario, provinceMap

    def _deserializeAction(self, actionEntry: Dict[str, Any], scenario: Scenario, provinceMap: Dict[int, Province]) -> Action:
        """
        Takes a serialized action entry from the replay JSON and reconstructs
        the corresponding Action object to be applied to the scenario during playback.

        Args:
            actionEntry (Dict[str, Any]): The serialized action entry.
            scenario (Scenario): The scenario to which the action will be applied.
            provinceMap (Dict[int, Province]): Mapping of province IDs to Province objects.

        Raises:
            ValueError: If the action type is not supported.

        Returns:
            Action: The deserialized Action object.
        """
        # First we get basic universal information about the action that is applicable regardless of type of action
        actionType = actionEntry["type"]
        isConsequence = actionEntry.get("isConsequence", False)
        data = actionEntry.get("data", {})
        factions = scenario.factions

        # Now we handle specific action types and reconstruct their data accordingly
        # See documentation of Action class for details
        if actionType == "moveUnit":
            # Again, we shall default to (0,0) coordinates if missing to help with debugging
            initRow, initCol = data.get("initial", [0, 0])
            finalRow, finalCol = data.get("final", [0, 0])

            initTile = scenario.mapData[initRow][initCol]
            finalTile = scenario.mapData[finalRow][finalCol]

            previousInitial = {"unit": initTile.unit, "owner": initTile.owner}
            previousFinal = {"unit": finalTile.unit, "owner": finalTile.owner}

            unitMoved = initTile.unit
            resultInitial = self._deserializeTileState(data.get("resultantInitial"), provinceMap, factions)

            # The overrideUnit is used in case the unit that moved
            # is the same as the one in the resultant final tile state
            overrideUnit = None
            if data.get("unitMovedMatchesResultantFinal"):
                overrideUnit = unitMoved

            resultFinal = self._deserializeTileState(data.get("resultantFinal"), provinceMap, factions, overrideUnit)
            moveData = {
                "initialHexCoordinates": (initRow, initCol),
                "finalHexCoordinates": (finalRow, finalCol),
                "previousInitialHexState": previousInitial,
                "previousFinalHexState": previousFinal,
                "resultantInitialHexState": resultInitial,
                "resultantFinalHexState": resultFinal,
                "unitMoved": unitMoved,
                "incomeFromMove": data.get("incomeFromMove", 0)
            }
            return Action("moveUnit", moveData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        if actionType == "tileChange":
            row, col = data.get("coordinates", [0, 0])
            tile = scenario.mapData[row][col]
            previousState = {"unit": tile.unit, "owner": tile.owner}
            newState = self._deserializeTileState(data.get("newTileState"), provinceMap, factions)
            tileRhangeData = {
                "hexCoordinates": (row, col),
                "newTileState": newState,
                "previousTileState": previousState,
                "costOfAction": data.get("costOfAction", 0)
            }
            return Action("tileChange", tileRhangeData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        if actionType == "provinceCreate":
            provinceId = data.get("provinceId")
            factionIndex = data.get("factionIndex", 0)
            faction = scenario.factions[factionIndex]
            province = provinceMap.get(provinceId)
            if province is None:
                province = Province(tiles=[], resources=data.get("resources", 0), faction=faction)
                provinceMap[provinceId] = province
                faction.provinces.append(province)
            province.resources = data.get("resources", province.resources)
            province.active = data.get("active", province.active)
            province.tiles = []
            initialTiles = []
            for row, col in data.get("initialTiles", []):
                tile = scenario.mapData[row][col]
                initialTiles.append(tile)
            createData = {
                "faction": faction,
                "province": province,
                "initialTiles": initialTiles
            }
            return Action("provinceCreate", createData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        if actionType == "provinceDelete":
            provinceId = data.get("provinceId")
            factionIndex = data.get("factionIndex", 0)
            faction = scenario.factions[factionIndex]
            province = provinceMap.get(provinceId)
            deleteData = {
                "faction": faction,
                "province": province
            }
            provinceState = data.get("provinceState")

            if provinceState and province is not None:
                provinceStateTiles = []
                for row, col in provinceState.get("tiles", []):
                    provinceStateTiles.append(scenario.mapData[row][col])
                deleteData["provinceState"] = {
                    "tiles": provinceStateTiles,
                    "resources": provinceState.get("resources", province.resources),
                    "active": provinceState.get("active", province.active)
                }
            return Action("provinceDelete", deleteData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        if actionType == "provinceResourceChange":
            province = provinceMap.get(data.get("provinceId"))
            resourceData = {
                "province": province,
                "previousResources": data.get("previousResources", 0),
                "newResources": data.get("newResources", 0)
            }
            return Action("provinceResourceChange", resourceData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        if actionType == "provinceActivationChange":
            province = provinceMap.get(data.get("provinceId"))
            activationData = {
                "province": province,
                "previousActiveState": data.get("previousActiveState", False),
                "newActiveState": data.get("newActiveState", False)
            }
            return Action("provinceActivationChange", activationData, isDirectConsequenceOfAnotherAction=isConsequence)
        
        # At this point every known action type has been handled
        # so if we reach here, it's an unsupported action type
        raise ValueError(f"Unsupported action type in replay playback: {actionType}")

    def _deserializeTileState(
        self,
        state: Optional[Dict[str, Any]],
        provinceMap: Dict[int, Province],
        factions: List[Faction],
        overrideUnit: Optional[Unit] = None
    ) -> Dict[str, Any]:
        """
        Deserializes the state of a tile, including its unit and owner province.
        The overrideUnit parameter allows for using an existing Unit object
        instead of deserializing a new one, useful in cases where the same
        unit instance is referenced in multiple places (for example, when a unit moves).

        Args:
            state (Optional[Dict[str, Any]]): The serialized state of the tile.
            provinceMap (Dict[int, Province]): Mapping of province IDs to Province objects.
            factions (List[Faction]): List of factions to resolve ownership.
            overrideUnit (Optional[Unit], optional): An existing Unit object to use instead of deserializing. Defaults to None.

        Returns:
            Dict[str, Any]: The deserialized state of the tile.
        """
        result: Dict[str, Any] = {}

        if state is None:
            return result
        
        if "unit" in state:
            # Only need to care about deserializing the unit
            # if we don't have an overrideUnit to use already
            if overrideUnit is not None:
                unitObj = overrideUnit
                data = state.get("unit") or {}
                unitObj.canMove = data.get("canMove", unitObj.canMove)
            else:
                unitObj = self._deserializeUnit(state.get("unit"), factions)
            result["unit"] = unitObj

        if "ownerProvinceId" in state:
            result["owner"] = provinceMap.get(state.get("ownerProvinceId"))

        return result

    def _setupNeighborsForMap(self, mapRows: List[List[HexTile]]) -> None:
        """
        Sets up the neighbors field for each HexTile in the map.
        See the following explanation copied from the Scenario class's __init__ function:

        mapData is a 2D array of HexTile objects representing the map.
        We do a simple map between the 2D "rectangular" array and
        the hexagonal grid by using offset coordinates.
        So for example, consider the following 2 by 5 grid:
        ASCII representation of hex grid:
            ___     ___     ___
           /0,0\___/0,2\___/0,4\
           \___/0,1\___/0,3\___/
           /1,0\___/1,2\___/1,4\
           \___/1,1\___/1,3\___/
               \___/   \___/
                   
        In this case, mapData[0][0] is hex tile (0,0),
        mapData[0][1] is hex tile (0,1), and so on.
        Basically, if we label columns of the hexagonal grid as "q" 
        and row as "r", then the hex tile at (r, q) is stored in
        mapData[r][q].
        
        Due to how hexagons are arranged, rows may rise and fall a 
        bit, but columns remain straight (see the diagram above).
        Also note that if 0,1 were above 0,0 rather than below it,
        the neighbor relationships would be different, 
        so it's important to understand that we start at 0,0
        with 0,0 being raised above 0,1.
        
        With this in mind, we can realize that if we have
        the i,j hex tile in mapData[i][j], and we want to find
        its neighbors, we can do so as follows:

        If j is even (0, 2, 4, ...):                   If j is odd (1, 3, 5, ...):
          North:     (i-1, j)                            North:     (i-1, j)
          Northeast: (i-1, j+1)                          Northeast: (i, j+1)
          Southeast: (i, j+1)                            Southeast: (i+1, j+1)
          South:     (i+1, j)                            South:     (i+1, j)
          Southwest: (i, j-1)                            Southwest: (i, j-1)
          Northwest: (i-1, j-1)                          Northwest: (i-1, j)
        """
        dimension = len(mapRows)
        for row in range(dimension):
            for col in range(len(mapRows[row])):
                tile = mapRows[row][col]
                neighbors = [None] * 6
                if col % 2 == 0:
                    if row > 0:
                        neighbors[0] = mapRows[row - 1][col]
                    if row > 0 and col + 1 < len(mapRows[row]):
                        neighbors[1] = mapRows[row - 1][col + 1]
                    if col + 1 < len(mapRows[row]):
                        neighbors[2] = mapRows[row][col + 1]
                    if row + 1 < dimension:
                        neighbors[3] = mapRows[row + 1][col]
                    if col > 0:
                        neighbors[4] = mapRows[row][col - 1]
                    if row > 0 and col > 0:
                        neighbors[5] = mapRows[row - 1][col - 1]
                else:
                    if row > 0:
                        neighbors[0] = mapRows[row - 1][col]
                    if col + 1 < len(mapRows[row]):
                        neighbors[1] = mapRows[row][col + 1]
                    if row + 1 < dimension and col + 1 < len(mapRows[row]):
                        neighbors[2] = mapRows[row + 1][col + 1]
                    if row + 1 < dimension:
                        neighbors[3] = mapRows[row + 1][col]
                    if row + 1 < dimension and col > 0:
                        neighbors[4] = mapRows[row + 1][col - 1]
                    if col > 0:
                        neighbors[5] = mapRows[row][col - 1]
                tile.neighbors = neighbors
