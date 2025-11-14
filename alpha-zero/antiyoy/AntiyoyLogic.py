"""
AntiyoyLogic.py - Board logic and encoding/decoding for Antiyoy game

This module provides the Board class which wraps the Scenario class
and handles conversion between the game's Python object representation
and the numpy array representation required by alpha-zero-general.
"""

import numpy as np
import sys
import os

# Add the parent directory to the path to import game modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
    HEIGHT = 6
    WIDTH = 6

    # Number of channels in the encoded board state
    # Channel 22 is reserved for action counter (encoded as scalar across all tiles)
    NUM_CHANNELS = 23

    # Action space configuration
    MAX_DESTINATIONS_PER_TILE = 20  # Conservative upper bound for movement options per tile
    NUM_UNIT_TYPES = 7  # soldierTier1-4, farm, tower1, tower2

    # Maximum actions per turn before forcing end turn
    # This prevents infinite loops in MCTS
    # Set to 1 initially for simpler gameplay (like traditional board games)
    MAX_ACTIONS_PER_TURN = 1

    # Maximum total turns before forcing a draw
    # Prevents infinite games where players just pass
    # Reduced to 50 to help MCTS terminate sooner
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
        Create a balanced starting scenario for 2 factions on a 6x6 board.

        Returns:
            Scenario object with initial game state
        """
        # Create 2 factions
        faction1 = Faction(name="Player 1", color="red", playerType="AI")
        faction2 = Faction(name="Player 2", color="blue", playerType="AI")
        factions = [faction1, faction2]

        # Generate a random scenario with balanced starting positions
        # Target ~20 land tiles out of 36 total, with each faction starting with 3 tiles
        scenario = generateRandomScenario(
            dimension=self.WIDTH,
            targetNumberOfLandTiles=20,
            factions=factions,
            initialProvinceSize=3,
            randomSeed=None  # Can set for reproducibility
        )

        # CRITICAL FIX: Give starting resources so games actually progress
        # Without resources, players can only pass turns indefinitely
        for faction in scenario.factions:
            for province in faction.provinces:
                province.resources = 30  # Enough to build some units

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
        max_resources = 200.0
        faction1_resources_norm = numpy_board[18, 0, 0] if numpy_board[0, 0, 0] > 0 else 0
        faction2_resources_norm = numpy_board[19, 0, 0] if numpy_board[1, 0, 0] > 0 else 0

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
                        can_move = numpy_board[17, row, col] > 0
                        unit = Soldier(tier=tier, owner=province1)
                        unit.canMove = can_move
                        break

                # Check for soldiers (Player 2)
                if unit is None:
                    for tier in range(1, 5):
                        if numpy_board[7 + tier - 1, row, col] > 0:
                            can_move = numpy_board[17, row, col] > 0
                            unit = Soldier(tier=tier, owner=province2)
                            unit.canMove = can_move
                            break

                # Check for structures
                if unit is None:
                    if numpy_board[11, row, col] > 0:  # Capital
                        unit = Structure("capital", owner=tile_owner)
                    elif numpy_board[12, row, col] > 0:  # Farm
                        unit = Structure("farm", owner=tile_owner)
                    elif numpy_board[13, row, col] > 0:  # Tower1
                        unit = Structure("tower1", owner=tile_owner)
                    elif numpy_board[14, row, col] > 0:  # Tower2
                        unit = Structure("tower2", owner=tile_owner)

                # Check for trees/gravestones
                if unit is None:
                    if numpy_board[15, row, col] > 0:  # Tree
                        unit = Tree(unitType="tree", owner=None)
                    elif numpy_board[16, row, col] > 0:  # Gravestone
                        unit = Tree(unitType="gravestone", owner=None)

                tile.unit = unit

        # Update province active status
        province1.active = len(province1.tiles) >= 2
        province2.active = len(province2.tiles) >= 2

        # Determine which faction's turn it is based on current_player
        # Player 1 = faction index 0, Player -1 = faction index 1
        faction_to_play_index = 0 if current_player == 1 else 1

        # Extract action counter and turn count from channel 22
        action_counter_norm = numpy_board[22, 0, 0]  # Top half
        turn_count_norm = numpy_board[22, 3, 0]      # Bottom half
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
        dimension = len(mapData)
        for row in range(dimension):
            for col in range(dimension):
                tile = mapData[row][col]
                neighbors = [None] * 6

                if col % 2 == 0:  # Even column
                    if row > 0:
                        neighbors[0] = mapData[row-1][col]
                    if row > 0 and col < dimension - 1:
                        neighbors[1] = mapData[row-1][col+1]
                    if col < dimension - 1:
                        neighbors[2] = mapData[row][col+1]
                    if row < dimension - 1:
                        neighbors[3] = mapData[row+1][col]
                    if col > 0:
                        neighbors[4] = mapData[row][col-1]
                    if row > 0 and col > 0:
                        neighbors[5] = mapData[row-1][col-1]
                else:  # Odd column
                    if row > 0:
                        neighbors[0] = mapData[row-1][col]
                    if col < dimension - 1:
                        neighbors[1] = mapData[row][col+1]
                    if row < dimension - 1 and col < dimension - 1:
                        neighbors[2] = mapData[row+1][col+1]
                    if row < dimension - 1:
                        neighbors[3] = mapData[row+1][col]
                    if col > 0:
                        neighbors[4] = mapData[row][col-1]
                    if row > 0 and col > 0:
                        neighbors[5] = mapData[row][col-1]

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
                for to_row in range(self.HEIGHT):
                    for to_col in range(self.WIDTH):
                        if (to_row, to_col) != (from_row, from_col):
                            # Calculate approximate hex distance (not perfect but consistent)
                            destinations.append((to_row, to_col))

                # Sort for consistency (lexicographic order)
                destinations.sort()

                # Take only the first MAX_DESTINATIONS_PER_TILE
                destinations = destinations[:self.MAX_DESTINATIONS_PER_TILE]

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

                        # Channel 17: Movement status
                        if unit.canMove:
                            board[17, row, col] = 1.0

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

                    # Channels 15-16: Trees and gravestones
                    elif isinstance(unit, Tree):
                        if unit.unitType == "tree":
                            board[15, row, col] = 1.0
                        elif unit.unitType == "gravestone":
                            board[16, row, col] = 1.0

                # Channels 18-19: Province resources (normalized)
                if tile.owner is not None:
                    if tile.owner.faction == faction1:
                        board[18, row, col] = faction1_resources_norm
                    elif tile.owner.faction == faction2:
                        board[19, row, col] = faction2_resources_norm

                # Channels 20-21: Province income (normalized)
                if tile.owner is not None:
                    if tile.owner.faction == faction1:
                        board[20, row, col] = faction1_income_norm
                    elif tile.owner.faction == faction2:
                        board[21, row, col] = faction2_income_norm

        # Channel 22: Action counter and turn count (encoded together)
        # Top half of tiles: action counter
        # Bottom half of tiles: turn counter
        action_counter_norm = self.actions_this_turn / self.MAX_ACTIONS_PER_TURN
        turn_count_norm = min(self.turn_count / self.MAX_GAME_TURNS, 1.0)

        # Fill top 3 rows with action counter, bottom 3 rows with turn counter
        board[22, :3, :] = action_counter_norm
        board[22, 3:, :] = turn_count_norm

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

    def get_valid_moves_vector(self):
        """
        Get a binary vector of valid actions.

        Returns:
            numpy array of shape (ACTION_SIZE,) with 1 for valid actions, 0 otherwise
        """
        valid = np.zeros(self.ACTION_SIZE, dtype=np.float32)

        # Get the current faction
        faction = self.scenario.getFactionToPlay()
        if faction is None:
            # If no faction, only end turn is valid
            valid[-1] = 1.0
            return valid

        # If we've reached max actions per turn, only allow end turn
        if self.actions_this_turn >= self.MAX_ACTIONS_PER_TURN:
            valid[-1] = 1.0
            return valid

        # Get all valid move actions
        for province in faction.provinces:
            if not province.active:
                continue

            for tile in province.tiles:
                # Check for movable soldiers
                if tile.unit is not None and isinstance(tile.unit, Soldier) and tile.unit.canMove:
                    # Get valid destinations
                    try:
                        destinations = self.scenario.getAllTilesWithinMovementRangeFiltered(
                            tile.row, tile.col
                        )

                        for dest_row, dest_col in destinations:
                            action = self.encode_move_action(tile.row, tile.col, dest_row, dest_col)
                            if action is not None and 0 <= action < self.MOVE_ACTIONS:
                                valid[action] = 1.0
                    except:
                        pass  # Skip if there's an error

                # Check for buildable units
                try:
                    buildable_units = self.scenario.getBuildableUnitsOnTile(
                        tile.row, tile.col, province
                    )

                    for unit_type in buildable_units:
                        action = self.encode_build_action(tile.row, tile.col, unit_type)
                        if action is not None and self.MOVE_ACTIONS <= action < self.MOVE_ACTIONS + self.BUILD_ACTIONS:
                            valid[action] = 1.0
                except:
                    pass  # Skip if there's an error

        # End turn is always valid
        valid[-1] = 1.0

        return valid

    def apply_action(self, action):
        """
        Apply an action to the board.

        Args:
            action: Integer action index

        Returns:
            True if successful, False otherwise
        """
        if self.is_end_turn_action(action):
            # End turn - advance to next faction and reset action counter
            actions_to_apply = self.scenario.advanceTurn()
            for act, prov in actions_to_apply:
                self.scenario.applyAction(act, prov)
            self.actions_this_turn = 0  # Reset counter for next turn
            self.turn_count += 1  # Increment total turn count
            return True

        # Check if we've reached max actions per turn
        # If so, force end turn instead of allowing more actions
        if self.actions_this_turn >= self.MAX_ACTIONS_PER_TURN:
            # Automatically end turn
            actions_to_apply = self.scenario.advanceTurn()
            for act, prov in actions_to_apply:
                self.scenario.applyAction(act, prov)
            self.actions_this_turn = 0
            self.turn_count += 1  # Increment total turn count
            return True

        # Try to decode as move action
        move_result = self.decode_move_action(action)
        if move_result is not None:
            from_row, from_col, to_row, to_col = move_result
            try:
                actions_to_apply = self.scenario.moveUnit(from_row, from_col, to_row, to_col)
                for act, prov in actions_to_apply:
                    self.scenario.applyAction(act, prov)
                self.actions_this_turn += 1  # Increment action counter
                return True
            except Exception as e:
                return False

        # Try to decode as build action
        build_result = self.decode_build_action(action)
        if build_result is not None:
            row, col, unit_type = build_result
            try:
                # Find the province that owns this tile
                tile = self.scenario.mapData[row][col]
                province = tile.owner

                if province is None:
                    return False

                actions_to_apply = self.scenario.buildUnitOnTile(row, col, unit_type, province)
                for act, prov in actions_to_apply:
                    self.scenario.applyAction(act, prov)
                self.actions_this_turn += 1  # Increment action counter
                return True
            except Exception as e:
                return False

        return False

    def check_game_ended(self, player):
        """
        Check if the game has ended and return the result for the given player.

        Args:
            player: 1 or -1

        Returns:
            0 if game not ended
            1 if player won
            -1 if player lost
            1e-4 for draw
        """
        # Check if max turns reached (force draw)
        if self.turn_count >= self.MAX_GAME_TURNS:
            return 1e-4  # Draw

        # Count active factions
        active_factions = []
        for faction in self.scenario.factions:
            if any(p.active for p in faction.provinces):
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
        if winner_faction == self.scenario.factions[0]:
            winner_player = 1
        else:
            winner_player = -1

        if winner_player == player:
            return 1
        else:
            return -1
