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

        # Health bar
        health_bar = HealthBar(entity=self)
        self.health_bar = self.entity_manager.add(health_bar)

    def damage(self, damage: int) -> None:
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

    assets_needed = {"idle": []}  # This is a placeholder

    def __init__(self, entity: AnimatedEntity):
        """A class to display a health bar.

        Args:
            entity (AnimatedEntity): The entity to display the health bar on.
        """
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=3)

        # Set attributes
        self.entity = entity

        # Set Private attributes
        self.current_hp = self.entity.hp
        self.max_hp = self.entity.max_hp

        # Create health bar animation
        animation = pygame.Surface((5, 50))
        animation.fill((255, 0, 0))
        pygame.draw.rect(
            animation, (0, 255, 0), (0, 0, 5, 50 * self.entity.hp / self.entity.max_hp)
        )
        self.create_animation(
            "idle",
            [animation],
        )

    def update(self, event_list: list) -> None:
        """Update the health bar."""
        # Update position
        self.x = self.entity.x
        self.y = self.entity.y - 15

        # Update health bar
        if self.current_hp != self.entity.hp or self.max_hp != self.entity.max_hp:
            self.create_animation(
                "idle",
                [self.__create_health_bar()],
            )

    def __create_health_bar(self):
        """Create a surface representing the health bar.

        Returns:
            pygame.Surface: The surface representing the health bar.
        """
        surface = pygame.Surface((5, 50))
        surface.fill((255, 0, 0))
        pygame.draw.rect(
            surface,
            (0, 255, 0),
            (0, 0, 5, 50 * self.entity.hp / self.entity.max_hp),
        )
        return surface
