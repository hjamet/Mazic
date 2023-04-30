import pygame
from EntityManager import Entity, AnimatedEntity


class Character(Entity, AnimatedEntity):
    assets_needed = {
        "idle": [
            "wizzard_m_idle_anim_f0",
            "wizzard_m_idle_anim_f1",
            "wizzard_m_idle_anim_f2",
            "wizzard_m_idle_anim_f3",
        ],
        "run": [
            "wizzard_m_run_anim_f0",
            "wizzard_m_run_anim_f1",
            "wizzard_m_run_anim_f2",
            "wizzard_m_run_anim_f3",
        ],
        "hit": [
            "wizzard_m_hit_anim_f0",
        ],
    }

    def __init__(self, name: str) -> None:
        """A class for the players character."""

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self)

        # Set attributes
        self.name = name

        # Set default attributes
        self.speed = 2

    def update(self, event_list: list) -> None:
        """Update the entity.

        Args:
            event_list (list): The events to process.

        Returns:
            list : The events the entity generated.
        """
        for event in event_list:
            # Move character
            if event.type == "move":
                self.__move(**event.data)

        return []

    def __move(self, direction: str) -> None:
        """Move the character in the given direction.

        Args:
            direction (str): The direction to move the character.
        """
        if direction == "up":
            self.y -= self.speed

        elif direction == "down":
            self.y += self.speed
        elif direction == "left":
            self.x -= self.speed
        elif direction == "right":
            self.x += self.speed
        else:
            raise ValueError(f"Invalid direction: {direction}")
