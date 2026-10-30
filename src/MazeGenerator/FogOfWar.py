from typing import Set, Tuple, Optional
import math


class FogOfWar:
    """Manages the Fog of War, line-of-sight raycasting, and tile exploration memory."""

    UNEXPLORED = "UNEXPLORED"
    EXPLORED = "EXPLORED"
    VISIBLE = "VISIBLE"

    def __init__(self, tile_size: int = 16, vision_radius_tiles: int = 8) -> None:
        self.tile_size = tile_size
        self.vision_radius_tiles = vision_radius_tiles
        self.visible_tiles: Set[Tuple[int, int]] = set()
        self.explored_tiles: Set[Tuple[int, int]] = set()
        self.arcane_sight_active: bool = False

    def bresenham_line(self, x0: int, y0: int, x1: int, y1: int):
        """Standard Bresenham's line algorithm returning a list of grid coordinates."""
        points = []
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1

        if dx > dy:
            err = dx / 2.0
            while x != x1:
                points.append((x, y))
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
            points.append((x, y))
        else:
            err = dy / 2.0
            while y != y1:
                points.append((x, y))
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
            points.append((x, y))

        return points

    def compute_fov(
        self,
        player_x: float,
        player_y: float,
        walls: Set[Tuple[int, int]],
        arcane_sight_active: Optional[bool] = None,
        extra_radius: int = 0,
    ) -> Set[Tuple[int, int]]:
        """Computes the set of visible tiles using 2D grid raycasting.

        Args:
            player_x (float): Player world x position.
            player_y (float): Player world y position.
            walls (Set[Tuple[int, int]]): Set of (gx, gy) wall coordinates.
            arcane_sight_active (bool, optional): If True, bypasses wall blocking.
            extra_radius (int): Extra radius in tiles.

        Returns:
            Set[Tuple[int, int]]: The set of currently visible tiles.
        """
        if arcane_sight_active is None:
            arcane_sight = self.arcane_sight_active
        else:
            arcane_sight = arcane_sight_active

        radius = self.vision_radius_tiles + (5 if arcane_sight else extra_radius)
        center_gx = int(player_x // self.tile_size)
        center_gy = int(player_y // self.tile_size)

        visible: Set[Tuple[int, int]] = {(center_gx, center_gy)}
        radius_sq = radius * radius

        # Raycast towards perimeter tiles to cast light rays
        for target_gx in range(center_gx - radius, center_gx + radius + 1):
            for target_gy in (center_gx - radius, center_gx + radius):
                pass

        # Raycast to every tile on the boundary of the bounding box
        boundary_targets = set()
        for x in range(center_gx - radius, center_gx + radius + 1):
            boundary_targets.add((x, center_gy - radius))
            boundary_targets.add((x, center_gy + radius))
        for y in range(center_gy - radius, center_gy + radius + 1):
            boundary_targets.add((center_gx - radius, y))
            boundary_targets.add((center_gx + radius, y))

        for tx, ty in boundary_targets:
            line = self.bresenham_line(center_gx, center_gy, tx, ty)
            for gx, gy in line:
                dist_sq = (gx - center_gx) ** 2 + (gy - center_gy) ** 2
                if dist_sq > radius_sq:
                    break

                visible.add((gx, gy))

                # Wall blocks line of sight unless Arcane Sight is active
                if not arcane_sight and (gx, gy) in walls and (gx, gy) != (center_gx, center_gy):
                    # The wall itself is visible, but line of sight ends here
                    break

        return visible

    def update(
        self,
        player_x: float,
        player_y: float,
        walls: Set[Tuple[int, int]],
        arcane_sight_active: Optional[bool] = None,
        extra_radius: int = 0,
    ) -> None:
        """Updates the visible tiles and persists them into explored tiles."""
        if arcane_sight_active is not None:
            self.arcane_sight_active = arcane_sight_active

        self.visible_tiles = self.compute_fov(
            player_x,
            player_y,
            walls,
            arcane_sight_active=self.arcane_sight_active,
            extra_radius=extra_radius,
        )
        self.explored_tiles.update(self.visible_tiles)

    def get_tile_visibility(self, gx: int, gy: int) -> str:
        """Returns the visibility status of a tile: VISIBLE, EXPLORED, or UNEXPLORED."""
        if (gx, gy) in self.visible_tiles:
            return self.VISIBLE
        elif (gx, gy) in self.explored_tiles:
            return self.EXPLORED
        return self.UNEXPLORED
