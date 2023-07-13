import numpy as np
import pygame

from EntityManager import Entity, AnimatedEntity


class Projectile(Entity, AnimatedEntity):
    """A basic fireball projectile.

    Args:
        Entity (Entity): A class giving the projectile the ability to process events.
        AnimatedEntity (AnimatedEntity): A class giving the projectile the ability to be animated and displayed.

    Returns:
        Projectile: A projectile instance.
    """

    assets_needed = {
        "idle": [
            "FB001",
            "FB002",
            "FB003",
            "FB004",
            "FB005",
        ],
    }

    animation_speed = {
        "idle": 0.25,
    }

    def __init__(self, x: int, y: int, target_x: int, target_y: int) -> None:
        """A class for the players character.

        Args:
            name (str): The name of the character.
            x (int): The x position of the launch point.
            y (int): The y position of the launch point.
            target_x (int): The x position of the target.
            target_y (int): The y position of the target.
        """

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=2, has_hitbox=True, has_mask=True)

        # Set attributes
        self.x = x
        self.y = y
        self.target_x = target_x
        self.target_y = target_y

        # Set default attributes
        self.speed = 2
        self.scope_time = 1000  # The time the projectile will exist for in ms

        # Set private attributes
        self.launch_time = pygame.time.get_ticks()
        self.__direction = (
            (
                (self.target_x - self.x)
                / (abs(self.target_x - self.x) + abs(self.target_y - self.y))
                * self.speed
            ),
            (
                (self.target_y - self.y)
                / (abs(self.target_x - self.x) + abs(self.target_y - self.y))
                * self.speed
            ),
        )

        # Set default animation
        reverse = False if self.target_x > self.x else True
        rotation = -np.degrees(
            np.arctan(abs(self.target_y - self.y) / abs(self.target_x - self.x))
        )
        # Calculate the rotation
        self.set_animation(
            animation="idle", reverse=reverse, rotation=rotation, size=0.5
        )

    def update(self, event_list: list) -> None:
        """Move the projectile.

        Args:
            event_list (list): The events to process.

        Returns:
            list : The events the entity generated.
        """
        # Move the projectile
        self.x += self.__direction[0]
        self.y += self.__direction[1]

        # Check if the projectile is out of scope
        if pygame.time.get_ticks() - self.launch_time > self.scope_time:
            self.entity_manager.remove(self)

        return []
