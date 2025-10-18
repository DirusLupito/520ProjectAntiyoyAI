class Action:
    """
    Represents an invertible action that mutates the game state,
    and specifically the state of a Scenario's tiles. 
    So this won't affect something like a Province or faction directly,
    but rather the HexTiles that make up that Province or are owned by that faction.
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
    """
    def __init__(self, actionType, data, isDirectConsequenceOfAnotherAction=False):
        self.actionType = actionType  # String representing the type of action
        self.data = data              # Dictionary holding all relevant data
        self.isDirectConsequenceOfAnotherAction = isDirectConsequenceOfAnotherAction
        # While the structure of data depends on actionType,
        # it should either be:
        # For "moveUnit" actions:
        # {
        #     "initialHexCoordinates": (x1, y1) with integer indices correponding 
        #      to where the initial HexTile object is in mapData in the Scenario,
        #     "finalHexCoordinates": (x2, y2) with integer indices correponding 
        #      to where the final HexTile object is in mapData in the Scenario,
        #     "previousInitialHexState": <previous state> as a map between
        #      some key, either "unit" or "owner", and their previous values,
        #     "previousFinalHexState": <previous state> as a map between
        #      some key, either "unit" or "owner", and their previous values,
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
        # The only things that can change as the result of an action are the unit on
        # a tile, and/or the owner of a tile.
    def invert(self):
        """
        Returns the inverse of this action.
        The inverse action, when applied after this action,
        should restore the game state to what it was before
        this action was applied.
        The inverse of an inverse action should be the original action.
        """
        if self.actionType == "moveUnit":
            invertedData = {
                "initialHexCoordinates": self.data["finalHexCoordinates"],
                "finalHexCoordinates": self.data["initialHexCoordinates"],
                "previousInitialHexState": self.data["previousFinalHexState"],
                "previousFinalHexState": self.data["previousInitialHexState"],
                "incomeFromMove": -self.data["incomeFromMove"]
            }
            return Action("moveUnit", invertedData)
        elif self.actionType == "tileChange":
            invertedData = {
                "hexCoordinates": self.data["hexCoordinates"],
                "newTileState": self.data["previousTileState"],
                "previousTileState": self.data["newTileState"],
                "costOfAction": -self.data["costOfAction"]
            }
            return Action("tileChange", invertedData)
        else:
            raise ValueError(f"Unknown action type: {self.actionType}")
