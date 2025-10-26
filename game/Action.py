class Action:
    """
    Represents an invertible action that mutates the game state.
    In order to maintain invertibility, actions need to store
    more information that one might initially think.

    For instance, moving a unit from one hex to another
    in which both hexes are part of the same province
    is simple, and only requires knowledge of the initial
    and final hex coordinates.

    But capturing a tile, or destroying an enemy unit 
    requires information about the previous state of the captured
    tile, or the destroyed unit, in order to be invertible.
    So we need to store a lot of extra information for all
    unit movement actions in case that movement results
    in more than just the unit changing hexes.

    Actions can also be the consequence of other actions,
    such as a capital spawning when a province loses its capital tile
    or provinces being merged when a tile change results
    in two provinces of the same faction becoming adjacent.
    In such a case, these additional actions need to be inverted
    as well when inverting the original action, and should
    not be independently invertible. So this is why the 
    Action class also has a field stating whether an action
    was a direct result of another action or not.

    See below for a comprehensive list of every possible action
    and what information is required to make it invertible.

    UNIT MOVEMENT:
    - Requires:
      - Initial hex coordinates
      - Final hex coordinates
      - Previous state of the final hex (in case unit movement
        results in tile capture or unit destruction)
      - Previous state of the initial hex
      - Income from the move (in case a tree is chopped down)
      
      While we can derive the previous state of the initial hex
      from the fact that a hex tile can only hold one unit at a time,
      (so if we know which unit moved, we know that the initial hex
      must now be empty), it is easier for the sake of the inversion
      function to just store the previous state of the initial hex
      as well.

    TILE CHANGES (Placing/removing a structure, or a unit)
    - Requires:
      - Hex coordinates of the affected tile
      - New state of the affected tile
      - Previous state of the affected tile
      - Cost of the action (in case of refunds on undo)

    PROVINCE CHANGES:
    - Requires:
      - Faction involved
      - Province involved
      - Initial and/or final state of the province (depending on action)
    """
    def __init__(self, actionType, data, isDirectConsequenceOfAnotherAction=False):
        self.actionType = actionType  # String representing the type of action
        self.data = data              # Dictionary holding all relevant data
        # While the structure of data depends on actionType,
        # it should either be:
        # For "moveUnit" actions:
        # {
        #     "initialHexCoordinates": (x1, y1) with integer indices correponding 
        #      to where the initial HexTile object is in mapData in the Scenario,
        #     "finalHexCoordinates": (x2, y2) with integer indices correponding 
        #      to where the final HexTile object is in mapData in the Scenario,
        #     "previousInitialHexState": <previous state> as a map between
        #      some key, either "unit" or "owner", and their previous values
        #      which gives the state of the initial hex before the move,
        #     "previousFinalHexState": <previous state> as a map between
        #      some key, either "unit" or "owner", and their previous values
        #      which gives the state of the final hex before the move,
        #     "resultantInitialHexState": <resultant state> as a map between
        #      some key, either "unit" or "owner", and their resultant values
        #      which gives the state of the initial hex after the move,
        #     "resultantFinalHexState": <resultant state> as a map between
        #      some key, either "unit" or "owner", and their resultant values
        #      which gives the state of the final hex after the move,
        #     "unitMoved": <unit> which is the unit that was moved (or merged),
        #     "incomeFromMove": <amount> as an integer
        # }
        # For "tileChange" actions:
        # {
        #     "hexCoordinates": (x, y) with integer indices correponding
        #      to where the HexTile object is in mapData in the Scenario,
        #     "newTileState": <new state> as a map between some key,
        #      either "unit" or "owner", and their new values,
        #     "previousTileState": <previous state> as a map between some key,
        #      either "unit" or "owner", and their previous values,
        #     "costOfAction": <amount> as an integer
        # }
        # For "provinceCreate" actions:
        # {
        #     "faction": <faction>,
        #     "province": <province>,
        #     "initialTiles": [<tiles>] Initial tiles to populate the province with
        # }
        # 
        # For "provinceDelete" actions:
        # {
        #     "faction": <faction>,
        #     "province": <province>,
        #     "provinceState": { Full state for restoration
        #         "tiles": [<tiles>],
        #         "resources": <amount>,
        #         "active": <boolean>
        #     }
        # }
        # 
        # For "provinceResourceChange" actions:
        # {
        #     "province": <province>,
        #     "previousResources": <amount>,
        #     "newResources": <amount>
        # }
        #
        # For "provinceActivationChange" actions:
        # {
        #     "province": <province>,
        #     "previousActiveState": <boolean>,
        #     "newActiveState": <boolean>
        # }

        # Indicates if this action was a direct consequence of another action
        self.isDirectConsequenceOfAnotherAction = isDirectConsequenceOfAnotherAction
        
    def invert(self):
        """
        Returns the inverse of this action.
        The inverse action, when applied after this action,
        should restore the game state to what it was before
        this action was applied.
        The inverse of an inverse action should be the original action.
        """
        # Handles inversions for unit movement actions
        if self.actionType == "moveUnit":
            invertedData = {
                "initialHexCoordinates": self.data["initialHexCoordinates"],
                "finalHexCoordinates": self.data["finalHexCoordinates"],
                "previousInitialHexState": self.data["resultantInitialHexState"],
                "previousFinalHexState": self.data["resultantFinalHexState"],
                "resultantInitialHexState": self.data["previousInitialHexState"],
                "resultantFinalHexState": self.data["previousFinalHexState"],
                "unitMoved": self.data["unitMoved"],
                "incomeFromMove": -self.data["incomeFromMove"]
            }
            return Action("moveUnit", invertedData)
        # Handles inversions for tile change actions
        elif self.actionType == "tileChange":
            invertedData = {
                "hexCoordinates": self.data["hexCoordinates"],
                "newTileState": self.data["previousTileState"],
                "previousTileState": self.data["newTileState"],
                "costOfAction": -self.data["costOfAction"]
            }
            return Action("tileChange", invertedData)
        
        # Handles inversions for province actions
        elif self.actionType == "provinceCreate":
            # Inverting province creation is deletion
            invertedData = {
                "faction": self.data["faction"],
                "province": self.data["province"],
                "provinceState": {
                    "tiles": self.data["province"].tiles.copy(),
                    "resources": self.data["province"].resources,
                    "active": self.data["province"].active
                }
            }
            return Action("provinceDelete", invertedData)
            
        elif self.actionType == "provinceDelete":
            # Inverting province deletion is restoration
            invertedData = {
                "faction": self.data["faction"],
                "province": self.data["province"]
            }
            return Action("provinceCreate", invertedData)
            
        elif self.actionType == "provinceResourceChange":
            # Swap previous and new resource amounts
            invertedData = {
                "province": self.data["province"],
                "previousResources": self.data["newResources"],
                "newResources": self.data["previousResources"]
            }
            return Action("provinceResourceChange", invertedData)
            
        elif self.actionType == "provinceActivationChange":
            # Swap previous and new active states
            invertedData = {
                "province": self.data["province"],
                "previousActiveState": self.data["newActiveState"],
                "newActiveState": self.data["previousActiveState"]
            }
            return Action("provinceActivationChange", invertedData)
        
        else:
            raise ValueError(f"Unknown action type: {self.actionType}")
        
    def __str__(self):
        return f"Action(type={self.actionType}, data={self.data})"
