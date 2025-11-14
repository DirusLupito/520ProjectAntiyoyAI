from copy import deepcopy
import math

import torch
from game.Action import Action
from game.world.factions.Province import Province
from game.world.units.Soldier import Soldier
from game.world.units.Structure import Structure
import gym
import numpy as np
from ai.utils.commonAIUtilityFunctions import checkTimeToBankruptProvince, isEnemyTile


# Lists of types in order for your action space
UNIT_TYPES = [
    "soldierTier1",
    "soldierTier2",
    "soldierTier3",
    "soldierTier4"
]

BUILDING_TYPES = [
    "farm",
    "tower1",
    "tower2"
]

# Reverse mapping for decoding if needed
UNIT_TYPE_TO_INDEX = {utype: i for i, utype in enumerate(UNIT_TYPES)}
BUILDING_TYPE_TO_INDEX = {btype: i for i, btype in enumerate(BUILDING_TYPES)}

class AntiyoyEnv(gym.Env):
    def __init__(self, scenario, faction):
        super(AntiyoyEnv, self).__init__()

        self.scenario = scenario
        self.faction_idx = faction

        self.num_tiles = len(self.scenario.mapData) * len(self.scenario.mapData[0])

        self.action_space_size = self.num_tiles * 13 + 1

        self.UNIT_TYPES = [
            "soldierTier1",
            "soldierTier2",
            "soldierTier3",
            "soldierTier4",
            "farm",
            "tower1",
            "tower2"
        ]

        # Track previous enemy units for reward calculation (if needed)
        # self.prev_enemy_attack = self._evaluate_enemy_force()
        self.prev_faction_tiles = self._count_faction_tiles()
        # self.prev_friendly_metric = self._evaluate_friendly_force()
        self.prev_farm_count = self._count_farms()
        self.enemy_tiles_claimed = 0
        self.prev_income = self._get_total_income()
        self.dumb_move_penalty = 0

    
    def index_to_coords(self, tile_index):
        """
        Converts a flat tile index to (row, col) tuple based on map size.

        Assumes a fixed square map size (self.max_tiles_sqrt x self.max_tiles_sqrt).
        Adjust if your map shape is rectangular or variable.
        """
        size = int(np.sqrt(self.num_tiles))
        row = tile_index // size
        col = tile_index % size
        return (row, col)

    def can_move_unit(self, unit):
        """
        Returns True if the unit can move (based on its 'canMove' attribute),
        False otherwise.
        """
        if unit is None:
            return False
        return unit.canMove

    def get_all_reachable_tiles(self, row, col):
        """
        Returns a list of (row, col) tuples for all tiles reachable by
        the unit at (row, col).

        Uses scenario's method getAllTilesWithinMovementRange.
        """
        return self.scenario.getAllTilesWithinMovementRange(row, col)
    
    def decode_action(self, action_idx):
        """
        How we convert action ids to real actions
        Currently only allows units to move one tile
        """
        NUM_TILES = self.num_tiles

        MOVE_UNIT_SIZE = NUM_TILES * 6  # 6 directions per tile for movement
        BUILD_UNIT_SIZE = NUM_TILES * len(self.UNIT_TYPES)


        # 1) Move unit
        if action_idx < MOVE_UNIT_SIZE:
            tile_index = action_idx // 6
            direction = action_idx % 6

            start_row, start_col = self.index_to_coords(tile_index)
            unit = self.scenario.mapData[start_row][start_col].unit

            if unit is None or unit.owner is None or unit.owner.name != self.scenario.factions[self.faction_idx].name or not self.can_move_unit(unit):
                # Invalid move action
                return None, None

            reachable_tiles = self.get_all_reachable_tiles(start_row, start_col)
            # Find destination tile based on direction
            # Assuming direction maps to neighbor index 0-5
            neighbors = self.scenario.mapData[start_row][start_col].neighbors
            dest_hex = neighbors[direction]

            if dest_hex is None:
                return None, None  # invalid direction (edge of map)

            dest_row, dest_col = dest_hex.row, dest_hex.col

            if (dest_row, dest_col) not in reachable_tiles:
                return None, None  # destination not reachable
            
            dest_owner = self.scenario.mapData[dest_row][dest_col].owner
            if dest_owner is not None and dest_owner not in self.scenario.factions[self.faction_idx].provinces:
                self.enemy_tiles_claimed += 1
            

            # Build the Action for unit movement
            actions = self.scenario.moveUnit(start_row, start_col, dest_row, dest_col)
            # print(f"Moving unit at ({start_row}, {start_col}) to ({dest_row}, {dest_col})")
            
            return actions, self.scenario.factions[self.faction_idx].provinces.index(self.scenario.mapData[start_row][start_col].owner)

        # 2) Build unit
        elif action_idx < MOVE_UNIT_SIZE + BUILD_UNIT_SIZE:
            offset = action_idx - MOVE_UNIT_SIZE
            tile_index = offset // len(self.UNIT_TYPES)
            unit_type_index = offset % len(self.UNIT_TYPES)

            row, col = self.index_to_coords(tile_index)
            unit_type_str = self.UNIT_TYPES[unit_type_index]

            dest_owner = self.scenario.mapData[row][col].owner
            if dest_owner is not None and dest_owner not in self.scenario.factions[self.faction_idx].provinces:
                self.enemy_tiles_claimed += 1

            for (i, province) in enumerate(self.scenario.factions[self.faction_idx].provinces):
                buildable = self.scenario.getBuildableUnitsOnTile(row, col, province)
                if unit_type_str in buildable:
                    actions = self.scenario.buildUnitOnTile(row, col, unit_type_str, self.scenario.factions[self.faction_idx].provinces[i])
                    break
            
            # print(f"Building {unit_type_str} at ({row}, {col})")
            return actions, i
        else:
            # Action index outside known range or end turn
            return None, None

    def step(self, action_idx):
        actions = []
        # decode the current action
        action, province_idx = self.decode_action(action_idx)
        # if it is end turn (should only happen during training)
        if action_idx == self.action_space_size - 1:
            # advance the turn and let the other ai play
            self.scenario.advanceTurn()
            from ai.AIPersonality import AIPersonality
            # can choose here which ai to play against
            ai_fn = AIPersonality.implementedAIs["mark1srb"]
            actions = ai_fn(self.scenario, self.scenario.getFactionToPlay())
            # perform its actions
            for act, prov in actions:
                self.scenario.applyAction(act, prov)
            # now back to our turn
            self.scenario.advanceTurn()
        # otherwise, if it is not end turn
        else:
            # perform the actions
            for a in action:
                if province_idx is None:
                    self.scenario.applyAction(a)
                else:

                    self.scenario.applyAction(a, self.scenario.factions[self.faction_idx].provinces[min(province_idx, len(self.scenario.factions[self.faction_idx].provinces) - 1)])
                actions.append([a, province_idx])
                
        activeFactions = 0
        for faction in self.scenario.factions:
            if any(province.active for province in faction.provinces):
                activeFactions += 1

        if activeFactions <= 1:
            obs = self._get_observation()
            reward = self._calculate_reward()
            return obs, reward, True, {}, []
        
        # Finally, get next observation and reward for the agent's turn
        obs = self._get_observation()
        reward = self._calculate_reward()
        move_mask = self.compute_valid_action_mask()
        info = {
            "moves": action,
            "valid_action_mask": move_mask
        }

        # print(f"Turn Reward: {reward:.2f}")

        return obs, reward, False, info, actions
    
    def render(self):
        self.scenario.displayMap()
    
    def _get_observation(self, debug=False):
        """
        Observes the scenario and converts it into a simple format to be used as input to the Neural Network
        Currently outputs:
            terrain_layer: 1 for water, 0 for land
            owner_layer: 1 for current faction owner, 2 for enemy
            building_layer: {'farm': 0, 'tower1': 1, 'tower2': 2, 'capital': 3, 'tree': 3}
            unit_layer: {'soldierTier1': 0, 'soldierTier2': 1, 'soldierTier3': 2, 'soldierTier4': 3}
        """
        mapData = self.scenario.mapData
        n_rows = len(mapData)
        n_cols = len(mapData[0])
        n_players = 2

        terrain_layer = np.zeros((n_rows, n_cols), dtype=np.float32)
        owner_layer = np.zeros((n_rows, n_cols, n_players), dtype=np.float32)
        
        max_building_types = 4
        max_unit_types = 4

        building_layer = np.zeros((n_rows, n_cols, max_building_types), dtype=np.float32)
        unit_layer = np.zeros((n_rows, n_cols, max_unit_types), dtype=np.float32)

        current_faction = self.scenario.factions[self.faction_idx]

        for r in range(n_rows):
            for c in range(n_cols):
                tile = mapData[r][c]

                terrain_layer[r, c] = 1.0 if tile.isWater else 0.0

                if tile.owner is not None and tile.owner.faction == current_faction:
                    owner_layer[r, c, 0] = 1.0
                elif tile.owner is not None:
                    owner_layer[r, c, 1] = 1.0

                if tile.unit is not None:
                    building_map = {'farm': 0, 'tower1': 1, 'tower2': 2, 'capital': 3, 'tree': 3}
                    btype = tile.unit.unitType
                    if btype in building_map:
                        building_layer[r, c, building_map[btype]] = 1.0

                    unit_map = {'soldierTier1': 0, 'soldierTier2': 1, 'soldierTier3': 2, 'soldierTier4': 3}
                    utype = tile.unit.unitType
                    if utype in unit_map:
                        unit_layer[r, c, unit_map[utype]] = 1.0

        if debug:
            return {
                "terrain": terrain_layer,
                "owner": owner_layer,
                "building": building_layer,
                "unit": unit_layer,
            }

        obs = np.concatenate([
            terrain_layer.flatten(),
            owner_layer.flatten(),
            building_layer.flatten(),
            unit_layer.flatten(),
        ]).astype(np.float32)

        # print({"terrain": terrain_layer,"owner": owner_layer,"building": building_layer,"unit": unit_layer})

        return obs
    
    def _collect_enemy_units(self):
        """
        Returns a list of enemy unit tiles on the map.
        """
        enemy_units = []
        for row in self.scenario.mapData:
            for tile in row:
                unit = getattr(tile, 'unit', None)
                if unit is None:
                    continue
                owner = getattr(unit, 'owner', None)
                # treat as enemy if owner exists and is NOT the current faction
                if owner != self.scenario.factions[self.faction_idx]:
                    # print(unit)
                    enemy_units.append(tile)
        return enemy_units
    
    def _collect_friendly_units(self):
        """
        Returns a list of friendly unit tiles on the map.
        """
        enemy_units = []
        for row in self.scenario.mapData:
            for tile in row:
                unit = tile.unit
                if unit is None or not unit.unitType.startswith('soldier'):
                    continue
                # print(unit)
                if unit.owner == self.scenario.factions[self.faction_idx]:
                    # print(f"Here: {unit}")
                    enemy_units.append(tile)
        return enemy_units


    # --- evaluate friendly force (attack-aware + prefers many weaker units) ---
    def _evaluate_friendly_force(self):
        """
        Compute a scalar value for the enemy force present on the map.
        This is designed to prioritize strong units on tiles near enemies
        """

        ON_BONUS = 9.0
        ADJACENT_BONUS = 6.0
        ONE_BACK_BONUS = 3.0

        friendly_units = self._collect_friendly_units()
        if not friendly_units:
            return 0.0

        faction = self.scenario.factions[self.faction_idx]
        score = 0.0

        for u in friendly_units:
            tile = u

            found_on = False
            found_adjacent = False
            found_one_back = False

            if isEnemyTile(tile, faction):
                found_on = True
                break

            # --- Adjacent tiles ---
            if not found_on:
                for n1 in tile.neighbors:
                    if n1 is not None and isEnemyTile(n1, faction):
                        found_adjacent = True
                        break

            if not found_adjacent and not found_on:
                # --- Distance 2 tiles (neighbors of neighbors) ---
                for n1 in tile.neighbors:
                    if n1 is not None:
                        for n2 in n1.neighbors:
                            if n2 is tile:  
                                continue  # skip the original tile
                            if n2 is not None and isEnemyTile(n2, faction):
                                found_one_back = True
                                break
                    if found_one_back:
                        break
            
            if found_on:
                score += ON_BONUS
            elif found_adjacent:
                score += ADJACENT_BONUS
            elif found_one_back:
                score += ONE_BACK_BONUS
            score *= 1 + ((tile.unit.attackPower - 1) *.5)

        return score


    # --- count farms (economy tiles) ---
    def _count_farms(self):
        """
        Count the number of farm/economy tiles owned by the current faction.
        The detection is flexible: looks for tile.is_farm, tile.building == 'farm', tile.terrain == 'farm', etc.
        """
        farm_count = 0
        for row in self.scenario.mapData:
            for tile in row:
                # ownership check (tile.owner might be faction object, index, or name)
                if tile.unit == None:
                    continue
                if not tile.unit.owner == self.scenario.factions[self.faction_idx]:
                    continue

                if tile.unit.unitType == 'farm':
                    farm_count += 1

        return farm_count


    # --- count province tiles (update - robust owner check) ---
    def _count_faction_tiles(self):
        """
        Counts how many tiles belong to the current province.
        This version uses a robust owner check consistent with tile ownership representation.
        """
        count = 0
        for row in self.scenario.mapData:
            for tile in row:
                # If tiles belong to "province" objects stored on faction, check accordingly:
                # If your data model stores provinces differently, adapt this check.
                # For now we treat a tile as in the faction's province if the tile.owner matches current faction.
                if tile.owner in self.scenario.factions[self.faction_idx].provinces:
                    count += 1
        return count
    
    def _calculate_bankruptcy(self):
        penalty = 0
        for province in self.scenario.factions[self.faction_idx].provinces:
            b_time = checkTimeToBankruptProvince(province)
            if b_time is not None and b_time > 0:
                penalty += 3/b_time
        return penalty
    
    def _get_total_income(self):
        income = 0
        for province in self.scenario.factions[self.faction_idx].provinces:
            income = province.computeIncome()
        return income


    # --- main reward calc ---
    def _calculate_reward(self):
        # multipliers (tweak to taste)
        ENEMY_UNIT_MULT = 2.0       # reward for eliminating enemy attack
        FACTION_MULT = 2.0          # reward per faction tile gained
        FARM_MULT = 10.0             # reward per new farm acquired
        ENEMY_TILE_MULT = 10.0
        BANKRUPT_MULT = -60.0
        INCOME_MULT = 3.0

        # --- friendly force metric and reward based on its change ---
        friendly_metric_reward = self._evaluate_friendly_force()
        # friendly_metric_reward = 0.0
        # friendly_metric_reward = (current_friendly_metric - self.prev_friendly_metric)
        # # store for next turn
        # self.prev_friendly_metric = current_friendly_metric

        # --- enemy force removal reward based on its change ---
        # current_enemy_attack = self._evaluate_enemy_force()
        # enemy_attack_reward = 0.0
        # enemy_attack_reward = (self.prev_enemy_attack - current_enemy_attack) * ENEMY_UNIT_MULT
        # # store for next turn
        # self.prev_enemy_attack = current_enemy_attack

        # --- province expansion reward (tiles gained) ---
        current_faction_tiles = self._count_faction_tiles()
        faction_expansion_reward = 0
        faction_expansion_reward = (current_faction_tiles - self.prev_faction_tiles) * FACTION_MULT
        self.prev_faction_tiles = current_faction_tiles

        # --- farm / economy reward ---
        current_farms = self._count_farms()
        farm_reward = 0
        farm_reward = (current_farms - self.prev_farm_count) * FARM_MULT
        self.prev_farm_count = current_farms

        # --- claim enemy tile reward ---
        claimed_enemy_tile_reward = self.enemy_tiles_claimed * ENEMY_TILE_MULT
        self.enemy_tiles_claimed = 0

        # --- bankruptcy penalty ---
        bankruptcy_penalty = self._calculate_bankruptcy() * BANKRUPT_MULT

        # --- income reward ---
        current_income = self._get_total_income()
        income_reward = current_income * INCOME_MULT
        
        # sum everything
        reward = friendly_metric_reward + faction_expansion_reward + farm_reward + claimed_enemy_tile_reward + bankruptcy_penalty + income_reward

        # Debugging info
        # print(f"Turn Reward: {reward:.2f}")
        # print(f"Friendly metric reward: {friendly_metric_reward:.2f}")
        # print(f"Faction expansion reward: {faction_expansion_reward:.2f} (tiles: {current_faction_tiles})")
        # print(f"Farm reward: {farm_reward:.2f} (farms: {current_farms})")
        # print(f"Enemy tile claimed reward: {claimed_enemy_tile_reward:.2f}")
        # print(f"Bankruptcy penalty: {bankruptcy_penalty:.2f}")
        # print(f"Income reward: {income_reward:.2f}")

        return reward
    
    def compute_valid_action_mask(self):
        """
        Computes which of the total possible moves are valid. Returns a tensor of entries True or False
        Currently only allows units to move one tile
        """
        num_tiles = self.num_tiles
        side = int(math.sqrt(num_tiles))

        move_mask_list = []
        build_mask = torch.zeros(num_tiles * len(self.UNIT_TYPES), dtype=torch.bool)

        # Move mask
        for start_row in range(side):
            for start_col in range(side):
                unit = self.scenario.mapData[start_row][start_col].unit

                # if unit is not None:
                #     print(unit.unitType)
                #     print(unit.owner)

                # Skip tiles with no movable unit or wrong owner
                if unit is None or unit.owner is None or unit.owner.name != self.scenario.factions[self.faction_idx].name or not self.can_move_unit(unit):
                        
                    # No moves from here
                    for _ in range(6):
                        move_mask_list.append(False)
                    continue

                # print("unit owner", unit.owner.name)
                # print("faction", self.scenario.factions[self.faction_idx].name)

                reachable_tiles = self.scenario.getAllTilesWithinMovementRangeFiltered(start_row, start_col)
                neighbors = self.scenario.mapData[start_row][start_col].neighbors

                for direction in range(6):
                    dest_hex = neighbors[direction]

                    if dest_hex is None:
                        move_mask_list.append(False)
                        continue

                    dest_row, dest_col = dest_hex.row, dest_hex.col
                    if (dest_row, dest_col) in reachable_tiles:
                        # print(f"{unit.unitType} at ({start_row}, {start_col}) can move to ({dest_row}, {dest_col})")
                        move_mask_list.append(True)
                    else:

                        move_mask_list.append(False)

        move_mask = torch.tensor(move_mask_list, dtype=torch.bool)

        # Buildable mask
        for tile_idx in range(num_tiles):
            x, y = divmod(tile_idx, side)
            faction = self.scenario.factions[self.faction_idx]
            all_buildable = []
            buildable = []
            for province in faction.provinces:
                buildable = self.scenario.getBuildableUnitsOnTile(x, y, province)
                all_buildable += buildable
            for build_type in buildable:
                if build_type in self.UNIT_TYPES and self.scenario.mapData[x][y].owner not in self.scenario.factions[self.faction_idx].provinces:
                    build_type_idx = self.UNIT_TYPES.index(build_type)
                    # print(f"{build_type} can be built on ({x}, {y})")
                    build_mask[tile_idx * len(self.UNIT_TYPES) + build_type_idx] = True


        # Combine
        combined_mask = torch.cat([move_mask, build_mask], dim=0)
        # End turn (last idx) always valid
        combined_mask = torch.cat([combined_mask, torch.tensor([True], device=combined_mask.device)])
        # print(combined_mask)
        return combined_mask