import pygame
from typing import Optional


class Ability:
    def __init__(self, name: str, cooldown: int):
        """An ability that an entity can use.

        Args:
            name (str): The name of the ability.
            cooldown (int): The cooldown of the ability in milliseconds.
        """
        self.name = name
        self.cooldown = cooldown


class AbilityManager:
    """An entity plugin to manage entity capabilities."""

    def __init__(self, entity_manager):
        """This class is used to manage entity capabilities.
        In particular, their cooldowns, names, evolutions, etc.
        """
        # Set attributes
        self.entity_manager = entity_manager

        # Set private attributes
        self.abilities = {}  # The abilities that the entity has.
        self.abilities_cooldown = (
            {}
        )  # The last time the ability was used. Used to calculate cooldowns.

    def add_ability(self, name: str, ability: Ability) -> None:
        """Add an ability to the entity.

        Args:
            name (str): The name of the ability.
            ability (Ability): The Ability object that will be created when the ability is used.
        """
        self.abilities[name] = ability
        self.abilities_cooldown[name] = 0

    def use_ability(self, name: str, kwargs: dict) -> Optional[Ability]:
        """

        Args:
            name (str): The name of the ability to use.

        Returns:
            Ability: The ability if it was used, None otherwise.
        """
        if name not in self.abilities:
            raise ValueError(f"Ability {name} not found in entity {self.id}")

        # Create ability
        ability = self.abilities[name](**kwargs)

        if pygame.time.get_ticks() - self.abilities_cooldown[name] > ability.cooldown:
            # Update last use time
            self.abilities_cooldown[name] = pygame.time.get_ticks()

            # Spawn ability
            self.entity_manager.add(ability)
