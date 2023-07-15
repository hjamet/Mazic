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
        self.health_bar = self.entity_manager.add(
            HealthBar,
            {
                "entity": self,
                "current_hp": self.hp,
                "max_hp": self.max_hp,
            },
        )

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

    assets_needed = {"idle": []}  # This is a placeholder

    def __init__(self, entity: AnimatedEntity, current_hp: int, max_hp: int):
        """A class to display a health bar.

        Args:
            entity (AnimatedEntity): The entity to display the health bar on.
            current_hp (int): The current number of hp the entity has.
            max_hp (int): The maximum number of hp the entity can have.
        """
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=3)

        # Set attributes
        self.entity = entity
        self.hp = current_hp
        self.max_hp = max_hp

        # Create health bar animation
        animation = pygame.Surface((5, 50))
        animation.fill((255, 0, 0))
        pygame.draw.rect(animation, (0, 255, 0), (0, 0, 5, 35))
        self.create_animation(
            "idle",
            [animation],
        )

    def update(self, event_list: list) -> None:
        """Update the health bar."""
        # Update position
        self.x = self.entity.x
        self.y = self.entity.y - 15
