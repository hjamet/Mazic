import pygame
from EntityManager import Entity, AnimatedEntity


class Health:
    """A parent class to manage health for entities.
    It includes taking damage, healing and health bar.
    """

    def __init__(self, max_hp: int) -> None:
        """A class to manage health for entities.

        Args:
            initial_hp (int): The initial health points.
        """
        # Set attributes
        self.max_hp = max_hp

        # Set default attributes
        self.hp = max_hp
        self._is_dead = False

    def take_damage(self, damage: int) -> None:
        """Take damage.

        Args:
            damage (int): The amount of damage to take.
        """
        self.hp -= damage
        if self.hp <= 0:
            self.hp = 0
            self._is_dead = True

    def heal(self, heal: int) -> None:
        """Heal.

        Args:
            heal (int): The amount of heal to take.
        """
        self.hp += heal
        if self.hp > self.max_hp:
            self.hp = self.max_hp


class HealthBar(Entity, AnimatedEntity):
    """A class to display a health bar.

    Args:
        Entity (Entity): A class giving the character the ability to process events.
        AnimatedEntity (AnimatedEntity): A class giving the character the ability to be displayed.
    """

    assets_needed = {
        "idle": [
            pygame.surface.Surface((100, 10)),
        ]
    }

    def __init__(self, current_hp: int, max_hp: int):
        """A class to display a health bar.

        Args:
            current_hp (int): The current number of hp the entity has.
            max_hp (int): The maximum number of hp the entity can have.
        """
        raise NotImplementedError
