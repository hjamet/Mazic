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

    def update(self, events: list) -> None:
        """Update the entity.

        Args:
            events (list): The events to process.

        Returns:
            list : The events the entity generated.
        """
        return []
