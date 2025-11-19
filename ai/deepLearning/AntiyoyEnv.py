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

        self.reachable_lists = None
        self.MAX_REACHABLE = None
        self._precompute_reachable_lists()

        self.action_space_size = self.num_tiles * (self.MAX_REACHABLE + 7) + 1

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
        self.dumb_move_penalty = 0
        self.tree_elim = 0
        self.prev_income, self.prev_resources = self._get_total_income()
        self.turn = 0

        

    def _precompute_reachable_lists(self, max_steps=4):
        """
        Precompute reachable tiles for every tile with a 'dummy unit'
        so we can build a static movement action space.
        """
        rows = len(self.scenario.mapData)
        cols = len(self.scenario.mapData[0])

        self.reachable_lists = []  # list of lists
        max_len = 0

        for r in range(rows):
            for c in range(cols):
                reachable = self._bfs_reachable(r, c, max_steps)
                # print(f"Tile ({r},{c}) reachable tiles ({len(reachable)}): {reachable}")
                self.reachable_lists.append(reachable)
                max_len = max(max_len, len(reachable))

        self.MAX_REACHABLE = max_len

        # Pad all lists to MAX_REACHABLE length with dummy invalid tile (-1, -1)
        for i, lst in enumerate(self.reachable_lists):
            if len(lst) < self.MAX_REACHABLE:
                padding = [(-1, -1)] * (self.MAX_REACHABLE - len(lst))
                self.reachable_lists[i] = lst + padding

    def _bfs_reachable(self, sr, sc, max_steps):
        from collections import deque
        visited = set()
        q = deque([(sr, sc, 0)])

        while q:
            r, c, dist = q.popleft()
            if dist > max_steps:
                continue
            if (r, c) in visited:
                continue

            visited.add((r, c))

            # Add neighbors
            for nb in self.scenario.mapData[r][c].neighbors:
                if nb is None:
                    continue
                # Skip water tiles if required by game rules
                if nb.isWater:
                    continue
                q.append((nb.row, nb.col, dist + 1))

        visited.remove((sr, sc))  # Remove the start tile itself
        return list(visited)

    
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
    
    def get_winner(self):
        activeFactions = []
        for faction in self.scenario.factions:
            if any(province.active for province in faction.provinces):
                activeFactions.append(faction)

        if len(activeFactions) <= 1:
            return activeFactions
        return None
    
    def decode_action(self, action_idx):
        """
        How we convert action ids to real actions
        Currently only allows units to move one tile
        """
        NUM_TILES = self.num_tiles

        MOVE_UNIT_SIZE = NUM_TILES * self.MAX_REACHABLE
        BUILD_UNIT_SIZE = NUM_TILES * len(self.UNIT_TYPES)

        actions = []


        # 1) Move unit
        if action_idx < MOVE_UNIT_SIZE:
            tile_index = action_idx // self.MAX_REACHABLE
            reach_idx = action_idx % self.MAX_REACHABLE

            num_cols = len(self.scenario.mapData[0])
            start_row, start_col = self.index_to_coords(tile_index)
            flat_index = start_row * num_cols + start_col

            reachable_list = self.reachable_lists[flat_index]
            dest_row, dest_col = reachable_list[reach_idx]
            
            dest_owner = self.scenario.mapData[dest_row][dest_col].owner
            if dest_owner is not None:
                if dest_owner not in self.scenario.factions[self.faction_idx].provinces:
                    self.enemy_tiles_claimed += 1
                elif dest_owner in self.scenario.factions[self.faction_idx].provinces:
                    if self.scenario.mapData[dest_row][dest_col].unit is not None and self.scenario.mapData[dest_row][dest_col].unit.unitType == 'tree':
                        self.tree_elim += 1
                    else:
                        self.dumb_move_penalty -= 1
                    

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
                    # print(f"Building {unit_type_str} at ({row}, {col})")
                    break
            
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
            ai_fn = AIPersonality.implementedAIs["mark2srb"]
            actions = ai_fn(self.scenario, self.scenario.factions[1-self.faction_idx])
            # ai_fn = AIPersonality.implementedAIs["ppo"]
            # actions = ai_fn(self.scenario, self.scenario.factions[1-self.faction_idx], train=False)
            # perform its actions
            for act, prov_idx in actions:
                if not isinstance(prov_idx, Province):
                    if prov_idx is None:
                        # Some actions don't need a province
                        self.scenario.applyAction(act, None)
                    else:
                        # Convert index → Province object
                        faction = self.scenario.getFactionToPlay()
                        prov_list = faction.provinces

                        # Clamp to avoid out-of-range issues
                        prov_obj = prov_list[min(prov_idx, len(prov_list) - 1)]

                        self.scenario.applyAction(act, prov_obj)
                else:
                    self.scenario.applyAction(act, prov_idx)
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
                actions.append([a, self.scenario.factions[self.faction_idx].provinces[min(province_idx, len(self.scenario.factions[self.faction_idx].provinces) - 1)]])
                
        if self.get_winner() is not None:
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

        current_income, current_resources = self._get_total_income()

        max_resources = 1000  # adjust based on your game's typical max
        max_income = 100

        normalized_resources = min(max_resources, current_resources) / max_resources
        normalized_income = min(max_income, current_income) / max_income

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
            np.array([normalized_resources, normalized_income], dtype=np.float32)
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
        ADJACENT_BONUS = 10.0
        ONE_BACK_BONUS = 5.0
        HIGH_TIER_PENALTY = -30.0   # tweak this value

        friendly_units = self._collect_friendly_units()
        if not friendly_units:
            return 0.0

        faction = self.scenario.factions[self.faction_idx]
        score = 0.0

        for tile in friendly_units:
            unit = tile.unit

            # Tier penalty (Tier >= 3)
            if unit.attackPower >= 3:
                score += HIGH_TIER_PENALTY

            found_adjacent = False
            found_one_back = False

            # Adjacent tiles
            for n1 in tile.neighbors:
                if n1 is not None and isEnemyTile(n1, faction):
                    found_adjacent = True
                    break

            # Distance-2 tiles only if nothing adjacent
            if not found_adjacent:
                for n1 in tile.neighbors:
                    if n1 is not None:
                        for n2 in n1.neighbors:
                            if n2 is tile:
                                continue
                            if n2 is not None and isEnemyTile(n2, faction):
                                found_one_back = True
                                break
                    if found_one_back:
                        break

            # Add bonuses
            if found_adjacent:
                score += ADJACENT_BONUS
            elif found_one_back:
                score += ONE_BACK_BONUS

            # Reward stronger units *only up to tier 2*
            # Tier 3+ already penalized above
            if unit.attackPower <= 2:
                score *= 1 + ((unit.attackPower - 1) * 0.5)

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
        min_time_to_bankrupt = None

        for province in self.scenario.factions[self.faction_idx].provinces:
            b_time = checkTimeToBankruptProvince(province)  # returns int turns or None
            if b_time is not None:
                if min_time_to_bankrupt is None or b_time < min_time_to_bankrupt:
                    min_time_to_bankrupt = b_time

        if min_time_to_bankrupt is None:
            return 0.0  # no bankruptcy risk

        # Return an inverse measure so smaller time = larger penalty
        # Add 1 to avoid division by zero if bankruptcy is immediate
        bankruptcy_score = 1.0 / (min_time_to_bankrupt + 1)
        return bankruptcy_score
    
    def _get_total_income(self):
        income = 0
        resources = 0
        for province in self.scenario.factions[self.faction_idx].provinces:
            income += province.computeIncome()
            resources += province.resources
        return income, resources
    
    def calculateFactionIncome(self, faction):
        """
        Computes tile-based income including farms for a faction.
        We use the formula: income = numTiles + 4 * numFarms,
        since each controlled tile provides 1 income,
        and each farm unit provides an additional 4 income.
        
        We also subtract out tree tiles, since a tile with a tree
        does not provide income.
        
        Inactive provinces do not contribute to income either.
        
        Args:
            faction: The Faction object for which to calculate income.
            
        Returns:
            int: The calculated income for the faction.
        """
        tileCount = 0
        farmCount = 0
        # getattr is safer than faction.provinces or province.tiles, or... etc directly,
        # since the latter could raise an exception if our objects are None.
        # We first iterate over every province owned by the faction.
        for province in getattr(faction, "provinces", []):
            # Invalid provinces do not contribute to income.
            if province is None or not getattr(province, "active", False):
                continue
            
            # Within each valid province, we count tiles and farms,
            # and subtract out tree tiles.
            for tile in getattr(province, "tiles", []):
                if tile is None:
                    continue
                
                tileCount += 1
                if tile.unit is not None and tile.unit.unitType == "farm":
                    farmCount += 1
                    
                if tile.unit is not None and tile.unit.unitType == "tree":
                    tileCount -= 1  # Trees negate the income from the tile
                    
        return tileCount + (4 * farmCount)
    
    def boardEvaluation(self, maximizerFaction):
        """
        Scores the scenario at the current state from the perspective of the maximizer faction.
        Called in the terminal nodes of the minimax search.
        
        This evaluation function computes the ratio of the maximizer faction's income
        to the total income of all factions. This encourages the AI to not only maximize its own income
        but also to make the opponents weaker. It also doesn't take into account unit upkeep costs,
        so that building an army is not penalized.
        
        Args:
            planningScenario: The Scenario object representing the current planning state.    
            maximizerFaction: The faction for which the score is being calculated.
        """
        # maximizerIncome / totalIncome
        totalIncome = 0
        maximizerIncome = 0
        
        # We compute income for each faction
        # using the formula defined in calculateFactionIncome.
        for faction in self.scenario.factions:
            factionIncome = self.calculateFactionIncome(faction)
            totalIncome += factionIncome
            
            if faction == maximizerFaction:
                maximizerIncome = factionIncome
        
        # Should not be possible to have zero total income
        # unless the game is over, but just in case we want
        # to avoid division by zero.
        if totalIncome <= 0:
            return 0.0
        
        return maximizerIncome / totalIncome


    # --- main reward calc ---
    def _calculate_reward(self):
        # # multipliers (tweak to taste)
        # FACTION_MULT = 20.0          # reward per faction tile gained
        # FARM_MULT = 40.0             # reward per new farm acquired
        # ENEMY_TILE_MULT = 10.0
        # BANKRUPT_MULT = -1000.0
        # INCOME_MULT = 10.0
        # DUMB_MOVE_MULT = 30.0
        # RESOURCE_MULT = 1.0
        # TREE_MULT = 30.0

        # # --- friendly force metric and reward based on its change ---
        # friendly_metric_reward = self._evaluate_friendly_force()

        # # --- province expansion reward (tiles gained) ---
        # current_faction_tiles = self._count_faction_tiles()
        # faction_expansion_reward = 0
        # faction_expansion_reward = (current_faction_tiles - self.prev_faction_tiles) * FACTION_MULT
        # self.prev_faction_tiles = current_faction_tiles

        # # --- farm / economy reward ---
        # current_farms = self._count_farms()
        # farm_reward = 0
        # farm_reward = (current_farms - self.prev_farm_count) * FARM_MULT
        # self.prev_farm_count = current_farms

        # # --- claim enemy tile reward ---
        # claimed_enemy_tile_reward = self.enemy_tiles_claimed * ENEMY_TILE_MULT
        # self.enemy_tiles_claimed = 0

        # # --- bankruptcy penalty ---
        # bankruptcy_penalty = self._calculate_bankruptcy() * BANKRUPT_MULT

        # # --- income reward ---
        # current_income, current_resources = self._get_total_income()
        # delta_income = current_income - self.prev_income
        # delta_resources = current_resources - self.prev_resources
        # income_reward = delta_income * INCOME_MULT
        # resource_reward = delta_resources * RESOURCE_MULT
        # self.prev_income = current_income
        # self.prev_resources = current_resources

        # dumb_move_penalty = self.dumb_move_penalty * DUMB_MOVE_MULT
        # self.dumb_move_penalty = 0

        tree_reward = self.tree_elim
        self.tree_elim = 0

        turn_length_penalty = max(-0.1, self.turn * -0.01)
        
        # sum everything
        # reward = friendly_metric_reward + faction_expansion_reward + farm_reward + claimed_enemy_tile_reward + bankruptcy_penalty + income_reward + dumb_move_penalty + resource_reward + tree_reward
        # reward = friendly_metric_reward + faction_expansion_reward + farm_reward + claimed_enemy_tile_reward + bankruptcy_penalty + income_reward + dumb_move_penalty + tree_reward
        # reward = income_reward + friendly_metric_reward + claimed_enemy_tile_reward + tree_reward + turn_length_penalty

        reward = self.boardEvaluation(self.scenario.factions[self.faction_idx]) - 0.5 + turn_length_penalty + (tree_reward * 0.1)

        # Debugging info
        # print(f"Turn Reward: {reward:.2f}")
        # print(f"Friendly metric reward: {friendly_metric_reward:.2f}")
        # print(f"Enemy tile claimed reward: {claimed_enemy_tile_reward:.2f}")
        # print(f"Income reward: {income_reward:.2f}")
        # print(f"Turn Penalty: {turn_length_penalty:.2f}")
        # print(f"Faction expansion reward: {faction_expansion_reward:.2f} (tiles: {current_faction_tiles})")
        # print(f"Farm reward: {farm_reward:.2f} (farms: {current_farms})")
        # print(f"Bankruptcy penalty: {bankruptcy_penalty:.2f}")
        # print(f"Resource reward: {resource_reward:.2f}")
        # print(f"Tree reward: {(tree_reward * 0.1):.2f}")
        # print(f"Dumb move penalty: {dumb_move_penalty:.2f}")

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
        for tile_index in range(self.num_tiles):
            r, c = self.index_to_coords(tile_index)
            unit = self.scenario.mapData[r][c].unit

            # No unit or wrong faction → all false
            if unit is None or unit.owner.name !=self.scenario.factions[self.faction_idx].name or not self.can_move_unit(unit):
                move_mask_list.extend([False] * self.MAX_REACHABLE)
                continue

            reachable_tiles = self.scenario.getAllTilesWithinMovementRangeFiltered(r, c)

            cols = len(self.scenario.mapData[0])
            index = r * cols + c
            reachable_list = self.reachable_lists[index]

            for item in reachable_list:
                rr, cc = item
                if rr == -1 or item not in reachable_tiles:
                    move_mask_list.append(False)
                else:
                    # print(f"{unit.unitType} at ({r}, {c}) can move to ({rr}, {cc})")
                    move_mask_list.append(True)

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
