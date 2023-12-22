from EntityManager import Entity, AnimatedEntity
from typing import Tuple
import pygame
from math import atan2, pi


class VisionLine(Entity, AnimatedEntity):
    """An invisible line for collision calculation of lines of sight."""

    assets_needed = {"idle": []}  # This is a placeholder

    def __init__(self, origin: Tuple[int, int], destination: Tuple[int, int]) -> None:
        """An invisible rectangle for calculating line-of-sight collisions.

        Args:
            origin (Tuple[int, int]): The origin of the line.
            destination (Tuple[int, int]): The destination of the line.
        """
        # Set attributes
        self.origin = origin
        self.destination = destination

        # Create rectangle
        ## Calculate rectangle dimensions
        width = 2
        height = int(
            ((destination[1] - origin[1]) ** 2 + (destination[0] - origin[0]) ** 2)
            ** 0.5
        )
        ## Create surface
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        ## Draw rectangle on surface
        pygame.draw.rect(surface, (255, 255, 255, 0), pygame.Rect(0, 0, width, height))
        ## Rotate surface
        angle = atan2(destination[1] - origin[1], destination[0] - origin[0]) * 180 / pi
        surface = pygame.transform.rotate(surface, angle)
        ## Set rectangle as asset
        self.assets_needed["idle"] = [surface]

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=1, has_hitbox=True, has_mask=False)
