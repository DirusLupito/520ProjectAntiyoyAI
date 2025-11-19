"""
AntiyoyLogic.py - Board logic and encoding/decoding for Antiyoy game

This module provides the Board class which wraps the Scenario class
and handles conversion between the game's Python object representation
and the numpy array representation required by alpha-zero-general.
"""

import numpy as np

from game.Scenario import Scenario
from game.world.factions.Faction import Faction
from game.world.HexTile import HexTile
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
from game.world.units.Tree import Tree
from game.world.factions.Province import Province
from game.scenarioGenerator import generateRandomScenario


class Board:
    """
    Wrapper around Scenario that handles encoding/decoding for alpha-zero-general.

    The board maintains a Scenario object and provides methods to:
    - Encode the game state to numpy arrays
    - Decode actions from integers
    - Get valid moves
    - Apply actions
    - Check game end conditions
    """

    # Board dimensions
    HEIGHT = 4
    WIDTH = 4

    # Number of channels in the encoded board state
    # Channel 21 is reserved for action counter (encoded as scalar across all tiles)
    NUM_CHANNELS = 22

    # Action space configuration
    MAX_DESTINATIONS_PER_TILE = 20  # Conservative upper bound for movement options per tile
    NUM_UNIT_TYPES = 7  # soldierTier1-4, farm, tower1, tower2

    # Maximum actions per turn before forcing end turn
    # This prevents infinite loops in MCTS
    # Set to 1 initially for simpler gameplay (like traditional board games)
    MAX_ACTIONS_PER_TURN = 1

    # Maximum total turns before forcing a draw
    # Prevents infinite games where players just pass
    MAX_GAME_TURNS = 50

    # Calculate action space size
    NUM_TILES = HEIGHT * WIDTH
    MOVE_ACTIONS = NUM_TILES * MAX_DESTINATIONS_PER_TILE
    BUILD_ACTIONS = NUM_TILES * NUM_UNIT_TYPES
    END_TURN_ACTION = 1
    ACTION_SIZE = MOVE_ACTIONS + BUILD_ACTIONS + END_TURN_ACTION

    # Unit type to index mapping for encoding build actions
    UNIT_TYPE_TO_INDEX = {
        "soldierTier1": 0,
        "soldierTier2": 1,
        "soldierTier3": 2,
        "soldierTier4": 3,
        "farm": 4,
        "tower1": 5,
        "tower2": 6
    }
    INDEX_TO_UNIT_TYPE = {v: k for k, v in UNIT_TYPE_TO_INDEX.items()}

    def __init__(self, scenario=None, current_player=1, actions_this_turn=0, turn_count=0):
        """
        Initialize the Board.

        Args:
            scenario: Scenario object (if None, creates a default 2-faction scenario)
            current_player: 1 or -1, representing which player's turn it is
            actions_this_turn: Number of actions taken this turn (default 0)
            turn_count: Total number of turns elapsed (default 0)
        """
        if scenario is None:
            scenario = self._create_initial_scenario()

        self.scenario = scenario
        self.current_player = current_player

        # Track number of actions taken this turn
        # This prevents infinite action sequences
        self.actions_this_turn = actions_this_turn

        # Track total number of turns in the game
        # This prevents infinite games
        self.turn_count = turn_count

        # Build destination lookup table for consistent action encoding
        self._build_destination_lookup()

    def _create_initial_scenario(self):
        """
        Create a balanced starting scenario for 2 factions.

        Returns:
            Scenario object with initial game state
        """
        # Create 2 factions
        faction1 = Faction(name="Player 1", color="red", playerType="AI")
        faction2 = Faction(name="Player 2", color="blue", playerType="AI")
        factions = [faction1, faction2]

        # Generate a random scenario with balanced starting positions
        total_tiles = self.WIDTH * self.HEIGHT
        target_land = self.WIDTH * self.HEIGHT
        scenario = generateRandomScenario(
            dimension=self.WIDTH,
            targetNumberOfLandTiles=target_land,
            factions=factions,
            initialProvinceSize=4,
            randomSeed=None  # Can set for reproducibility
        )

        for faction in scenario.factions:
            for province in faction.provinces:
                province.resources = 10

        return scenario

    @classmethod
    def from_numpy(cls, numpy_board, current_player=1):
        """
        Reconstruct a Board object from a numpy array representation.

        This method creates a new Scenario by decoding the numpy array.
        Note: This is a simplified reconstruction that creates one province per faction.

        Args:
            numpy_board: numpy array of shape (NUM_CHANNELS, HEIGHT, WIDTH)
            current_player: 1 or -1

        Returns:
            Board object
        """
        # Create 2 factions
        faction1 = Faction(name="Player 1", color="red", playerType="AI")
        faction2 = Faction(name="Player 2", color="blue", playerType="AI")
        factions = [faction1, faction2]

        # Create empty map
        mapData = []
        for row in range(cls.HEIGHT):
            mapRow = []
            for col in range(cls.WIDTH):
                tile = HexTile(row, col, isWater=False)
                mapRow.append(tile)
            mapData.append(mapRow)

        # Set up hex neighbors
        cls._setup_hex_neighbors_static(mapData)

        # Create provinces (one per faction initially)
        province1 = Province(faction=faction1)
        province2 = Province(faction=faction2)
        faction1.provinces = [province1]
        faction2.provinces = [province2]

        # Decode the numpy array
        # Extract resource values (denormalized)
        # Resources are encoded on every tile owned by the faction, so we can read from any owned tile
        max_resources = 200.0
        faction1_resources_norm = 0
        faction2_resources_norm = 0

        # Find any tile owned by each faction to read resources
        for row in range(cls.HEIGHT):
            for col in range(cls.WIDTH):
                if faction1_resources_norm == 0 and numpy_board[0, row, col] > 0:  # Faction 1 owns this tile
                    faction1_resources_norm = numpy_board[17, row, col]
                if faction2_resources_norm == 0 and numpy_board[1, row, col] > 0:  # Faction 2 owns this tile
                    faction2_resources_norm = numpy_board[18, row, col]
                # Break early if we've found both
                if faction1_resources_norm > 0 and faction2_resources_norm > 0:
                    break
            if faction1_resources_norm > 0 and faction2_resources_norm > 0:
                break

        province1.resources = int(faction1_resources_norm * max_resources)
        province2.resources = int(faction2_resources_norm * max_resources)

        # Decode tiles
        for row in range(cls.HEIGHT):
            for col in range(cls.WIDTH):
                tile = mapData[row][col]

                # Set water status
                if numpy_board[2, row, col] > 0:
                    tile.isWater = True
                    continue

                # Determine ownership
                tile_owner = None
                if numpy_board[0, row, col] > 0:  # Player 1 owns
                    tile_owner = province1
                    province1.tiles.append(tile)
                elif numpy_board[1, row, col] > 0:  # Player 2 owns
                    tile_owner = province2
                    province2.tiles.append(tile)

                tile.owner = tile_owner

                # Decode units
                unit = None

                # Check for soldiers (Player 1)
                for tier in range(1, 5):
                    if numpy_board[3 + tier - 1, row, col] > 0:
                        can_move = numpy_board[16, row, col] > 0
                        unit = Soldier(tier=tier, owner=faction1)
                        unit.canMove = can_move
                        break

                # Check for soldiers (Player 2)
                if unit is None:
                    for tier in range(1, 5):
                        if numpy_board[7 + tier - 1, row, col] > 0:
                            can_move = numpy_board[16, row, col] > 0
                            unit = Soldier(tier=tier, owner=faction2)
                            unit.canMove = can_move
                            break

                # Check for structures
                if unit is None:
                    # Structures need faction as owner, not province
                    structure_owner = tile_owner.faction if tile_owner is not None else None
                    if numpy_board[11, row, col] > 0:  # Capital
                        unit = Structure("capital", owner=structure_owner)
                    elif numpy_board[12, row, col] > 0:  # Farm
                        unit = Structure("farm", owner=structure_owner)
                    elif numpy_board[13, row, col] > 0:  # Tower1
                        unit = Structure("tower1", owner=structure_owner)
                    elif numpy_board[14, row, col] > 0:  # Tower2
                        unit = Structure("tower2", owner=structure_owner)

                # Check for trees (gravestones removed - purely visual)
                if unit is None:
                    if numpy_board[15, row, col] > 0:  # Tree
                        unit = Tree(isGravestone=False, owner=None)

                tile.unit = unit

        # Update province active status
        province1.active = len(province1.tiles) >= 2
        province2.active = len(province2.tiles) >= 2

        # IMPORTANT: When using canonical form (as MCTS does), the board is always
        # normalized so that the current player's faction is in channel 0.
        # Therefore, faction_to_play should always be 0 when using canonical form.
        # Since current_player==1 indicates canonical form (current player's perspective),
        # we always use faction 0 in that case.
        # When current_player==-1, the board represents the opponent's perspective,
        # so we use faction 1.
        faction_to_play_index = 0 if current_player == 1 else 1

        # Extract action counter and turn count from channel 21
        action_counter_norm = numpy_board[21, 0, 0]  # Top half
        turn_count_norm = numpy_board[21, 3, 0]      # Bottom half
        # Use rounding instead of truncation to handle floating point precision
        actions_this_turn = int(action_counter_norm * cls.MAX_ACTIONS_PER_TURN + 0.5)
        turn_count = int(turn_count_norm * cls.MAX_GAME_TURNS + 0.5)

        # Create scenario
        scenario = Scenario("Reconstructed", mapData, factions, indexOfFactionToPlay=faction_to_play_index)

        # Create and return Board with action counter and turn count passed directly
        # This ensures they're set BEFORE any initialization that might hit recursion limits
        board = cls(
            scenario=scenario,
            current_player=current_player,
            actions_this_turn=actions_this_turn,
            turn_count=turn_count
        )
        return board

    @staticmethod
    def _setup_hex_neighbors_static(mapData):
        """
        Set up hex neighbors for a map. Static version for use in from_numpy.
        """
        height = len(mapData)
        if height == 0:
            return
        width = len(mapData[0])

        for row in range(height):
            for col in range(width):
                tile = mapData[row][col]
                neighbors = [None] * 6

                if col % 2 == 0:  # Even column
                    if row > 0:
                        neighbors[0] = mapData[row-1][col]
                    if row > 0 and col < width - 1:
                        neighbors[1] = mapData[row-1][col+1]
                    if col < width - 1:
                        neighbors[2] = mapData[row][col+1]
                    if row < height - 1:
                        neighbors[3] = mapData[row+1][col]
                    if col > 0:
                        neighbors[4] = mapData[row][col-1]
                    if row > 0 and col > 0:
                        neighbors[5] = mapData[row-1][col-1]
                else:  # Odd column
                    if row > 0:
                        neighbors[0] = mapData[row-1][col]
                    if col < width - 1:
                        neighbors[1] = mapData[row][col+1]
                    if row < height - 1 and col < width - 1:
                        neighbors[2] = mapData[row+1][col+1]
                    if row < height - 1:
                        neighbors[3] = mapData[row+1][col]
                    if col > 0:
                        neighbors[4] = mapData[row][col-1]
                    if row > 0 and col > 0:
                        neighbors[5] = mapData[row-1][col-1]

                tile.neighbors = neighbors

    def _build_destination_lookup(self):
        """
        Build lookup tables for consistent move action encoding/decoding.

        For each tile, we need a consistent ordering of possible destination tiles.
        This creates a mapping from (from_tile_idx, to_tile_idx) -> destination_offset
        """
        self.destination_lookup = {}  # (from_idx, to_idx) -> offset
        self.reverse_destination_lookup = {}  # (from_idx, offset) -> to_idx

        # For each potential starting tile
        for from_row in range(self.HEIGHT):
            for from_col in range(self.WIDTH):
                from_idx = from_row * self.WIDTH + from_col

                # Get all tiles within reasonable movement range (up to 4 hexes + attacks)
                # We'll use a simple approach: consider all tiles within Manhattan distance
                destinations = []
                height = int(self.HEIGHT)
                width = int(self.WIDTH)
                for to_row in range(height):
                    for to_col in range(width):
                        if (to_row, to_col) != (from_row, from_col):
                            # Calculate approximate hex distance (not perfect but consistent)
                            destinations.append((to_row, to_col))

                # Sort for consistency (lexicographic order)
                destinations.sort()

                # Validate destinations list integrity
                for i, d in enumerate(destinations):
                    if not isinstance(d, tuple) or len(d) != 2:
                        raise ValueError(f"Destinations corrupted at index {i}: {d} (type: {type(d)}), from_tile=({from_row},{from_col})")

                # Take only the first MAX_DESTINATIONS_PER_TILE
                max_dest = int(self.MAX_DESTINATIONS_PER_TILE)
                destinations = destinations[:max_dest]

                # Build lookup tables
                for offset, (to_row, to_col) in enumerate(destinations):
                    to_idx = to_row * self.WIDTH + to_col
                    self.destination_lookup[(from_idx, to_idx)] = offset
                    self.reverse_destination_lookup[(from_idx, offset)] = to_idx

    def get_numpy_board(self):
        """
        Encode the current Scenario state to a numpy array.

        Returns:
            numpy array of shape (NUM_CHANNELS, HEIGHT, WIDTH)
        """
        board = np.zeros((self.NUM_CHANNELS, self.HEIGHT, self.WIDTH), dtype=np.float32)

        # Get the two factions
        if len(self.scenario.factions) != 2:
            raise ValueError("Board must have exactly 2 factions")

        faction1 = self.scenario.factions[0]
        faction2 = self.scenario.factions[1]

        # Calculate total resources and income for each faction
        faction1_resources = sum(p.resources for p in faction1.provinces if p.active)
        faction2_resources = sum(p.resources for p in faction2.provinces if p.active)
        faction1_income = sum(p.computeIncome() for p in faction1.provinces if p.active)
        faction2_income = sum(p.computeIncome() for p in faction2.provinces if p.active)

        # Normalize resources and income (cap at reasonable values)
        max_resources = 200.0
        max_income = 50.0
        faction1_resources_norm = min(faction1_resources / max_resources, 1.0)
        faction2_resources_norm = min(faction2_resources / max_resources, 1.0)
        faction1_income_norm = min(max(faction1_income / max_income, -1.0), 1.0)  # Can be negative
        faction2_income_norm = min(max(faction2_income / max_income, -1.0), 1.0)

        # Encode the board
        for row in range(self.HEIGHT):
            for col in range(self.WIDTH):
                tile = self.scenario.mapData[row][col]

                # Channel 0-1: Tile ownership
                if tile.owner is not None:
                    if tile.owner.faction == faction1:
                        board[0, row, col] = 1.0
                    elif tile.owner.faction == faction2:
                        board[1, row, col] = 1.0

                # Channel 2: Water tiles
                if tile.isWater:
                    board[2, row, col] = 1.0

                # Encode units if present
                if tile.unit is not None:
                    unit = tile.unit

                    # Determine which faction owns this unit
                    unit_faction_idx = None
                    if tile.owner is not None:
                        if tile.owner.faction == faction1:
                            unit_faction_idx = 0
                        elif tile.owner.faction == faction2:
                            unit_faction_idx = 1

                    # Channels 3-10: Soldiers by tier and faction
                    if isinstance(unit, Soldier):
                        tier = unit.tier
                        if unit_faction_idx == 0:  # Player 1 soldiers
                            board[3 + tier - 1, row, col] = 1.0
                        elif unit_faction_idx == 1:  # Player 2 soldiers
                            board[7 + tier - 1, row, col] = 1.0

                        # Channel 16: Movement status
                        if unit.canMove:
                            board[16, row, col] = 1.0

                    # Channels 11-14: Structures
                    elif isinstance(unit, Structure):
                        if unit.unitType == "capital":
                            board[11, row, col] = 1.0
                        elif unit.unitType == "farm":
                            board[12, row, col] = 1.0
                        elif unit.unitType == "tower1":
                            board[13, row, col] = 1.0
                        elif unit.unitType == "tower2":
                            board[14, row, col] = 1.0

                    # Channel 15: Trees only (gravestones removed - purely visual)
                    elif isinstance(unit, Tree):
                        if unit.unitType == "tree":
                            board[15, row, col] = 1.0

                # Channels 17-18: Province resources (normalized)
                if tile.owner is not None:
                    if tile.owner.faction == faction1:
                        board[17, row, col] = faction1_resources_norm
                    elif tile.owner.faction == faction2:
                        board[18, row, col] = faction2_resources_norm

                # Channels 19-20: Province income (normalized)
                if tile.owner is not None:
                    if tile.owner.faction == faction1:
                        board[19, row, col] = faction1_income_norm
                    elif tile.owner.faction == faction2:
                        board[20, row, col] = faction2_income_norm

        # Channel 21: Action counter and turn count (encoded together)
        # Top half of tiles: action counter
        # Bottom half of tiles: turn counter
        action_counter_norm = self.actions_this_turn / self.MAX_ACTIONS_PER_TURN
        turn_count_norm = min(self.turn_count / self.MAX_GAME_TURNS, 1.0)

        # Fill top 3 rows with action counter, bottom 3 rows with turn counter
        board[21, :3, :] = action_counter_norm
        board[21, 3:, :] = turn_count_norm

        return board

    def clone(self):
        """
        Create a deep copy of this Board.

        Returns:
            A new Board object with cloned Scenario
        """
        cloner = self.scenario.clone()
        cloned_scenario = cloner.getScenarioClone()
        cloned_board = Board(
            scenario=cloned_scenario,
            current_player=self.current_player,
            actions_this_turn=self.actions_this_turn,
            turn_count=self.turn_count
        )
        return cloned_board

    def encode_move_action(self, from_row, from_col, to_row, to_col):
        """
        Encode a move action as an integer.

        Args:
            from_row, from_col: Starting tile coordinates
            to_row, to_col: Destination tile coordinates

        Returns:
            Integer action index, or None if invalid
        """
        from_idx = from_row * self.WIDTH + from_col
        to_idx = to_row * self.WIDTH + to_col

        # Look up the destination offset
        key = (from_idx, to_idx)
        if key not in self.destination_lookup:
            return None  # Invalid move (not in our encoding)

        offset = self.destination_lookup[key]
        action = from_idx * self.MAX_DESTINATIONS_PER_TILE + offset

        return action

    def decode_move_action(self, action):
        """
        Decode a move action from an integer.

        Args:
            action: Integer action index

        Returns:
            Tuple (from_row, from_col, to_row, to_col) or None if invalid
        """
        if action < 0 or action >= self.MOVE_ACTIONS:
            return None

        from_idx = action // self.MAX_DESTINATIONS_PER_TILE
        offset = action % self.MAX_DESTINATIONS_PER_TILE

        # Look up the destination tile
        key = (from_idx, offset)
        if key not in self.reverse_destination_lookup:
            return None

        to_idx = self.reverse_destination_lookup[key]

        from_row = from_idx // self.WIDTH
        from_col = from_idx % self.WIDTH
        to_row = to_idx // self.WIDTH
        to_col = to_idx % self.WIDTH

        return (from_row, from_col, to_row, to_col)

    def encode_build_action(self, row, col, unit_type):
        """
        Encode a build action as an integer.

        Args:
            row, col: Tile coordinates
            unit_type: String like "soldierTier1", "farm", etc.

        Returns:
            Integer action index
        """
        if unit_type not in self.UNIT_TYPE_TO_INDEX:
            return None

        tile_idx = row * self.WIDTH + col
        unit_idx = self.UNIT_TYPE_TO_INDEX[unit_type]
        action = self.MOVE_ACTIONS + tile_idx * self.NUM_UNIT_TYPES + unit_idx

        return action

    def decode_build_action(self, action):
        """
        Decode a build action from an integer.

        Args:
            action: Integer action index

        Returns:
            Tuple (row, col, unit_type) or None if invalid
        """
        if action < self.MOVE_ACTIONS or action >= self.MOVE_ACTIONS + self.BUILD_ACTIONS:
            return None

        adjusted = action - self.MOVE_ACTIONS
        tile_idx = adjusted // self.NUM_UNIT_TYPES
        unit_idx = adjusted % self.NUM_UNIT_TYPES

        if unit_idx not in self.INDEX_TO_UNIT_TYPE:
            return None

        row = tile_idx // self.WIDTH
        col = tile_idx % self.WIDTH
        unit_type = self.INDEX_TO_UNIT_TYPE[unit_idx]

        return (row, col, unit_type)

    def is_end_turn_action(self, action):
        """Check if an action is the end turn action."""
        return action == self.ACTION_SIZE - 1

    def get_valid_moves_vector(self, debug=False):
        """
        Get a binary vector of valid actions.

        Args:
            debug: If True, print debug information about valid moves

        Returns:
            numpy array of shape (ACTION_SIZE,) with 1 for valid actions, 0 otherwise
        """
        valid = np.zeros(self.ACTION_SIZE, dtype=np.float32)

        # Get the current faction
        faction = self.scenario.getFactionToPlay()
        if faction is None:
            # If no faction, only end turn is valid
            if debug:
                print("[ValidMoves Debug] No faction to play - only END_TURN valid")
            valid[-1] = 1.0
            return valid

        # If we've reached max actions per turn, only allow end turn
        if self.actions_this_turn >= self.MAX_ACTIONS_PER_TURN:
            if debug:
                print(f"[ValidMoves Debug] Max actions reached ({self.actions_this_turn} >= {self.MAX_ACTIONS_PER_TURN}) - only END_TURN valid")
            valid[-1] = 1.0
            return valid

        if debug:
            print(f"[ValidMoves Debug] Checking faction with {len(faction.provinces)} provinces")

        # Get all valid move actions
        num_move_actions = 0
        num_build_actions = 0

        for province in faction.provinces:
            if not province.active:
                continue

            if debug:
                income = province.computeIncome()
                print(f"[ValidMoves Debug] Province: {len(province.tiles)} tiles, {province.resources} resources, income={income}, active={province.active}")

            for tile in province.tiles:
                # Check for movable soldiers
                if tile.unit is not None and isinstance(tile.unit, Soldier) and tile.unit.canMove:
                    # Get valid destinations
                    try:
                        destinations = self.scenario.getAllTilesWithinMovementRangeFiltered(
                            tile.row, tile.col
                        )

                        if debug and len(destinations) > 0:
                            print(f"[ValidMoves Debug] Soldier at ({tile.row},{tile.col}) can move to {len(destinations)} tiles")

                        for dest_row, dest_col in destinations:
                            action = self.encode_move_action(tile.row, tile.col, dest_row, dest_col)
                            if action is not None and 0 <= action < self.MOVE_ACTIONS:
                                valid[action] = 1.0
                                num_move_actions += 1
                    except Exception as e:
                        if debug:
                            print(f"[ValidMoves Debug] Error getting moves for ({tile.row},{tile.col}): {e}")
                        pass  # Skip if there's an error

                # Check for buildable units on this tile (owned by province)
                try:
                    buildable_units = self.scenario.getBuildableUnitsOnTile(
                        tile.row, tile.col, province
                    )

                    if debug and len(buildable_units) > 0:
                        print(f"[ValidMoves Debug] Can build on ({tile.row},{tile.col}): {buildable_units}")

                    for unit_type in buildable_units:
                        action = self.encode_build_action(tile.row, tile.col, unit_type)
                        if action is not None and self.MOVE_ACTIONS <= action < self.MOVE_ACTIONS + self.BUILD_ACTIONS:
                            valid[action] = 1.0
                            num_build_actions += 1
                except Exception as e:
                    if debug:
                        print(f"[ValidMoves Debug] Error getting buildable units for ({tile.row},{tile.col}): {e}")
                    pass  # Skip if there's an error

                # Also check neighboring tiles for capture opportunities
                for neighbor in tile.neighbors:
                    if neighbor is None or neighbor.isWater:
                        continue
                    # Only check tiles not owned by this province (enemy or neutral)
                    if neighbor.owner != province:
                        try:
                            buildable_units = self.scenario.getBuildableUnitsOnTile(
                                neighbor.row, neighbor.col, province
                            )

                            if debug and len(buildable_units) > 0:
                                print(f"[ValidMoves Debug] Can CAPTURE ({neighbor.row},{neighbor.col}): {buildable_units}")

                            for unit_type in buildable_units:
                                action = self.encode_build_action(neighbor.row, neighbor.col, unit_type)
                                if action is not None and self.MOVE_ACTIONS <= action < self.MOVE_ACTIONS + self.BUILD_ACTIONS:
                                    valid[action] = 1.0
                                    num_build_actions += 1
                        except Exception as e:
                            if debug:
                                print(f"[ValidMoves Debug] Error checking capture for ({neighbor.row},{neighbor.col}): {e}")
                            pass  # Skip if there's an error

        # End turn handling: prevent END_TURN if no actions have been taken yet
        # and other valid moves exist (forced action behavior)
        num_valid_before_end = int(np.sum(valid[:-1]))  # Count non-END_TURN valid moves

        if self.actions_this_turn == 0 and num_valid_before_end > 0:
            # Don't allow ending turn if we haven't taken any actions yet
            # and we have other valid moves available
            if debug:
                print(f"[ValidMoves Debug] END_TURN masked (actions_taken=0, {num_valid_before_end} alternatives exist)")
        else:
            # Allow END_TURN normally
            valid[-1] = 1.0

        if debug:
            print(f"[ValidMoves Debug] Found {num_move_actions} move actions, {num_build_actions} build actions")

        return valid

    def apply_action(self, action, debug=False):
        """
        Apply an action to the board.

        Args:
            action: Integer action index
            debug: If True, print debug information

        Returns:
            True if successful, False otherwise
        """
        if self.is_end_turn_action(action):
            # End turn - advance to next faction and reset action counter
            self.turn_count += 1  # Increment total turn count
            actions_to_apply = self.scenario.advanceTurn()
            for act, prov in actions_to_apply:
                self.scenario.applyAction(act, prov)
            self.actions_this_turn = 0  # Reset counter for next turn
            return True

        # Try to decode as move action
        move_result = self.decode_move_action(action)

        if move_result is not None:
            from_row, from_col, to_row, to_col = move_result
            try:
                actions_to_apply = self.scenario.moveUnit(from_row, from_col, to_row, to_col)
                for act in actions_to_apply:
                    self.scenario.applyAction(act, None)
                self.actions_this_turn += 1  # Increment action counter

                # Check if we've now reached max actions per turn
                # If so, force end turn
                if self.actions_this_turn >= self.MAX_ACTIONS_PER_TURN:
                    self.turn_count += 1  # Increment total turn count
                    actions_to_apply = self.scenario.advanceTurn()
                    for act, prov in actions_to_apply:
                        self.scenario.applyAction(act, prov)
                    self.actions_this_turn = 0

                return True
            except Exception as e:
                # Action failed - log for debugging
                import logging
                logging.debug(f"Move action {action} failed: {e}")
                return False

        # Try to decode as build action
        build_result = self.decode_build_action(action)

        if build_result is not None:
            row, col, unit_type = build_result
            try:
                # Find the province that owns this tile
                tile = self.scenario.mapData[row][col]
                province = tile.owner

                # For capturing neutral/enemy tiles, use current faction's province
                if province is None or province.faction != self.scenario.getFactionToPlay():
                    # Use current faction's active province for capturing
                    current_faction = self.scenario.getFactionToPlay()
                    if current_faction is None:
                        return False

                    # Find first active province
                    province = None
                    for prov in current_faction.provinces:
                        if prov.active:
                            province = prov
                            break

                    if province is None:
                        return False

                actions_to_apply = self.scenario.buildUnitOnTile(row, col, unit_type, province)
                for act in actions_to_apply:
                    self.scenario.applyAction(act, province)
                self.actions_this_turn += 1  # Increment action counter

                # Check if we've now reached max actions per turn
                # If so, force end turn
                if self.actions_this_turn >= self.MAX_ACTIONS_PER_TURN:
                    self.turn_count += 1  # Increment total turn count
                    actions_to_apply = self.scenario.advanceTurn()
                    for act, prov in actions_to_apply:
                        self.scenario.applyAction(act, prov)
                    self.actions_this_turn = 0

                return True
            except Exception as e:
                # Action failed - log for debugging
                import logging
                logging.debug(f"Build action {action} failed: {e}")
                return False

        # Action didn't match any known type
        return False

    def check_game_ended(self, player, debug=False):
        """
        Check if the game has ended and return the result for the given player.

        Args:
            player: 1 or -1
            debug: If True, print debug information

        Returns:
            0 if game not ended
            1 if player won
            -1 if player lost
            1e-4 for draw
        """
        # Check if max turns reached - determine winner by score instead of draw
        if self.turn_count >= self.MAX_GAME_TURNS:
            # Calculate score for each faction (tiles + resources/10)
            faction_scores = []
            for faction in self.scenario.factions:
                total_tiles = 0
                total_resources = 0
                for province in faction.provinces:
                    if province.active:
                        total_tiles += len(province.tiles)
                        total_resources += province.resources
                score = total_tiles + (total_resources / 10.0)
                faction_scores.append(score)

            # Determine winner based on score
            if abs(faction_scores[0] - faction_scores[1]) < 0.5:
                # Very close game, call it a draw
                return 1e-4
            elif faction_scores[0] > faction_scores[1]:
                # factions[0] is ahead (current player's perspective)
                # Return 1 for decisive win (same as normal victory)
                return 1.0
            else:
                # factions[1] is ahead (opponent's perspective)
                # Return -1 for decisive loss (same as normal loss)
                return -1.0

        # Count active factions
        active_factions = []
        for faction in self.scenario.factions:
            active_provinces = [p for p in faction.provinces if p.active]
            if active_provinces:
                active_factions.append(faction)

        if len(active_factions) > 1:
            # Game still ongoing
            return 0

        if len(active_factions) == 0:
            # Draw (no active factions)
            return 1e-4

        # One faction wins
        winner_faction = active_factions[0]

        # Determine which player the winner corresponds to
        # NOTE: When using canonical form, the board is always from the current player's perspective.
        # The board was reconstructed via from_numpy(board, player), which means:
        # - Channel 0 data → factions[0] (represents the "player" perspective)
        # - Channel 1 data → factions[1] (represents the opponent)
        #
        # Since canonical form swaps channels when player=-1, factions[0] always
        # represents the player from whose perspective we're checking.
        if winner_faction == self.scenario.factions[0]:
            # The current player (from whose perspective the board was constructed) won
            return 1
        else:
            # The opponent won
            return -1

    def evaluate_position(self):
        """
        Evaluate the current board position using a heuristic function.

        This is used when MCTS reaches max depth and needs a position evaluation
        instead of a true terminal outcome. Returns a value in [-1, 1] representing
        how good the position is for the current player (factions[0] in canonical form).

        The heuristic is based on income ratio: maximizer_income / total_income.
        This encourages the AI to maximize its own income while weakening opponents.

        Returns:
            float: Position evaluation in range [-1, 1]
                   Positive = good for current player (factions[0])
                   Negative = good for opponent (factions[1])
        """
        # Calculate income for both factions
        faction1 = self.scenario.factions[0]  # Current player in canonical form
        faction2 = self.scenario.factions[1]  # Opponent

        income1 = _calculateFactionIncome(faction1)
        income2 = _calculateFactionIncome(faction2)
        total_income = income1 + income2

        # Avoid division by zero
        if total_income <= 0:
            return 0.0

        # Calculate ratio from current player's perspective
        # Returns value in [0, 1], need to convert to [-1, 1]
        ratio = income1 / total_income

        # Convert [0, 1] to [-1, 1]
        # ratio=0.5 (equal) -> 0
        # ratio=1.0 (all income) -> 1
        # ratio=0.0 (no income) -> -1
        return 2.0 * ratio - 1.0

    def get_step_reward(self, player):
        """
        Calculate intermediate reward for the current board state.

        Rewards are based on:
        - Tiles owned (valuable for territory control)
        - Trees are OBSTACLES that reduce productivity (BAD!)
        - Capturing tree tiles removes obstacles (GOOD!)

        Reward structure (from player's perspective):
        - Each tile owned by player: +1
        - Each tile owned by opponent: -1
        - Each tree on player tile: -1 (BAD - trees hurt you!)
        - Each tree on opponent tile: +1 (GOOD - trees hurt them!)
        - Each tree on neutral tile: +0.5 (capturing removes obstacle)

        Args:
            player: 1 or -1 (player from whose perspective to calculate reward)

        Returns:
            float: Reward value scaled to be significant but not overwhelming
        """
        reward = 0.0

        # Get factions (in canonical form, factions[0] is always current player)
        player_faction = self.scenario.factions[0]
        opponent_faction = self.scenario.factions[1]

        # Count tiles and trees for each faction
        player_tiles = 0
        player_trees = 0  # Trees on YOUR tiles (BAD!)
        opponent_tiles = 0
        opponent_trees = 0  # Trees on THEIR tiles (GOOD - hurts them!)
        neutral_trees = 0

        for faction in self.scenario.factions:
            is_player_faction = (faction == player_faction)

            for province in faction.provinces:
                if not province.active:
                    continue

                for tile in province.tiles:
                    if is_player_faction:
                        player_tiles += 1
                        # Check for tree on player tile (BAD!)
                        if tile.unit is not None and tile.unit.unitType == "tree":
                            player_trees += 1
                    else:
                        opponent_tiles += 1
                        # Check for tree on opponent tile (GOOD - hurts them!)
                        if tile.unit is not None and tile.unit.unitType == "tree":
                            opponent_trees += 1

        # Count neutral tiles with trees
        # (tiles not owned by either faction but have trees)
        for row in range(self.HEIGHT):
            for col in range(self.WIDTH):
                tile = self.scenario.mapData[row][col]
                if tile is None:
                    continue

                # Check if tile is neutral (no faction ownership)
                tile_is_neutral = True
                for faction in self.scenario.factions:
                    for province in faction.provinces:
                        if province.active and tile in province.tiles:
                            tile_is_neutral = False
                            break
                    if not tile_is_neutral:
                        break

                if tile_is_neutral and tile.unit is not None and tile.unit.unitType == "tree":
                    neutral_trees += 1

        # Calculate reward components
        tile_reward = player_tiles - opponent_tiles
        tree_punish = -player_trees  # Penalty for having trees on your tiles
        neutral_tree_reward = neutral_trees * 0.5

        total_reward = tile_reward + tree_punish + neutral_tree_reward

        # Scale by 0.05 to keep rewards meaningful but not overwhelming compared to win/loss
        # Win/loss is +1/-1, so we want cumulative step rewards to be < 1.0
        # With ~20 turns/game and full board control (~5 tiles), total would be ~5.0
        # After scaling by 0.05, that's ~0.25, which guides learning without dominating win/loss
        scaled_reward = total_reward * 0.05

        # Safety check: ensure reward is not NaN or Inf (can cause segfaults)
        if np.isnan(scaled_reward) or np.isinf(scaled_reward):
            import logging
            log = logging.getLogger(__name__)
            log.error(f"Invalid reward detected! tile_reward={tile_reward}, tree_punish={tree_punish}, "
                     f"neutral_tree_reward={neutral_tree_reward}, total={total_reward}, scaled={scaled_reward}")
            return 0.0

        return scaled_reward


def _calculateFactionIncome(faction):
    """
    Helper function to compute tile-based income including farms for a faction.

    Formula: income = numTiles + 4 * numFarms
    - Each controlled tile provides 1 income
    - Each farm provides an additional 4 income
    - Trees negate the tile's income contribution
    - Inactive provinces do not contribute

    Args:
        faction: The Faction object for which to calculate income

    Returns:
        int: The calculated income for the faction
    """
    tile_count = 0
    farm_count = 0

    # Iterate over every province owned by the faction
    for province in getattr(faction, "provinces", []):
        # Inactive provinces do not contribute to income
        if province is None or not getattr(province, "active", False):
            continue

        # Within each valid province, count tiles and farms
        for tile in getattr(province, "tiles", []):
            if tile is None:
                continue

            tile_count += 1

            # Check for farms (add extra income)
            if tile.unit is not None and tile.unit.unitType == "farm":
                farm_count += 1

            # Trees negate the income from the tile
            if tile.unit is not None and tile.unit.unitType == "tree":
                tile_count -= 1

    return tile_count + (4 * farm_count)
