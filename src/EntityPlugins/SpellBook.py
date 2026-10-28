import math
from typing import Optional, Set, Tuple, Dict, Any, List


class SpellBook:
    """Manages player mana, inventory of spells and relics, and Mazic spellcasting."""

    SPELL_COSTS = {
        "fireball": 10,
        "wall_alter": 25,
        "arcane_sight": 20,
        "blink": 30,
    }

    def __init__(
        self,
        max_mana: float = 100.0,
        mana_regen_rate: float = 8.0,
    ) -> None:
        self.max_mana: float = float(max_mana)
        self.mana: float = float(max_mana)
        self.mana_regen_rate: float = float(mana_regen_rate)

        self.inventory: Dict[str, Any] = {
            "relics": 0,
            "crystals": 0,
            "spells": ["fireball", "wall_alter", "arcane_sight", "blink"],
        }

        self.arcane_sight_timer: float = 0.0

    @property
    def is_arcane_sight_active(self) -> bool:
        return self.arcane_sight_timer > 0.0

    def update(self, dt: float) -> None:
        """Regenerates mana and updates active spell durations.

        Args:
            dt (float): Elapsed time in seconds.
        """
        if dt > 0:
            self.mana = min(self.max_mana, self.mana + self.mana_regen_rate * dt)
            if self.arcane_sight_timer > 0:
                self.arcane_sight_timer = max(0.0, self.arcane_sight_timer - dt)

    def cast_fireball(
        self,
        origin: Tuple[float, float],
        target: Tuple[float, float],
    ) -> Optional[Dict[str, Any]]:
        """Casts an offensive fireball towards a target position.

        Args:
            origin (Tuple[float, float]): (x, y) start coordinates.
            target (Tuple[float, float]): (x, y) target coordinates.

        Returns:
            Optional[Dict[str, Any]]: Spell data dict or None if insufficient mana.
        """
        cost = self.SPELL_COSTS["fireball"]
        if self.mana < cost:
            return None

        self.mana -= cost
        return {
            "spell": "fireball",
            "origin": origin,
            "target": target,
            "damage": 25,
            "mana_spent": cost,
        }

    def cast_wall_alter(
        self,
        gx: int,
        gy: int,
        walls_set: set,
        floors_set: set,
    ) -> Optional[str]:
        """Alters the labyrinth layout: destroys an internal wall or builds a wall on floor.

        Args:
            gx (int): Tile grid x coordinate.
            gy (int): Tile grid y coordinate.
            walls_set (set): Mutable set of (gx, gy) wall coordinates.
            floors_set (set): Mutable set of (gx, gy) floor coordinates.

        Returns:
            Optional[str]: 'DESTROYED_WALL', 'CREATED_WALL', or None if invalid/insufficient mana.
        """
        cost = self.SPELL_COSTS["wall_alter"]
        if self.mana < cost:
            return None

        coord = (gx, gy)
        if coord in walls_set:
            walls_set.remove(coord)
            floors_set.add(coord)
            self.mana -= cost
            return "DESTROYED_WALL"
        elif coord in floors_set:
            floors_set.remove(coord)
            walls_set.add(coord)
            self.mana -= cost
            return "CREATED_WALL"

        return None

    def cast_arcane_sight(self, duration: float = 6.0) -> bool:
        """Activates Arcane Sight, penetrating walls and extending vision radius.

        Args:
            duration (float): Duration in seconds.

        Returns:
            bool: True if successfully cast, False if insufficient mana.
        """
        cost = self.SPELL_COSTS["arcane_sight"]
        if self.mana < cost:
            return False

        self.mana -= cost
        self.arcane_sight_timer = max(self.arcane_sight_timer, duration)
        return True

    def cast_blink(
        self,
        current_pos: Tuple[float, float],
        target_pos: Tuple[float, float],
        walls_set: set,
        floors_set: set,
        max_range_tiles: int = 6,
    ) -> Optional[Tuple[float, float]]:
        """Teleports the mage to a target walkable position within range.

        Args:
            current_pos (Tuple[float, float]): Current (x, y) world position.
            target_pos (Tuple[float, float]): Desired (x, y) world position.
            walls_set (set): Set of (gx, gy) wall coordinates.
            floors_set (set): Set of (gx, gy) floor coordinates.
            max_range_tiles (int): Maximum range in 16px tiles.

        Returns:
            Optional[Tuple[float, float]]: New position if valid, None otherwise.
        """
        cost = self.SPELL_COSTS["blink"]
        if self.mana < cost:
            return None

        cx, cy = current_pos
        tx, ty = target_pos

        dist = math.hypot(tx - cx, ty - cy)
        max_dist = max_range_tiles * 16.0
        if dist > max_dist:
            return None

        tgx = int(tx // 16)
        tgy = int(ty // 16)

        # Target must not be inside a wall
        if (tgx, tgy) in walls_set:
            return None

        # If floors_set is specified, target must be on a floor
        if floors_set and (tgx, tgy) not in floors_set:
            return None

        self.mana -= cost
        return (float(tx), float(ty))
