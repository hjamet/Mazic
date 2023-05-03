import pygame
from EntityManager import Entity, AnimatedEntity
from typing import List, Tuple


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

    animation_speed = {
        "idle": 0.05,
        "run": 0.2,
        "hit": 0.1,
    }

    def __init__(self, name: str) -> None:
        """A class for the players character."""

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=2, hitbox=True)

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
        animation = {"animation": "idle", "reverse": None}
        for event in event_list:
            # Move character
            if event.type == "move":
                animation = self.__move(**event.data)

        # Update animation
        self.set_animation(**animation)

        return []

    def __move(self, direction: str) -> None:
        """Move the character in the given direction.

        Args:
            direction (str): The direction to move the character.
        """
        reverse = None

        x, y = self.x, self.y
        if direction == "up":
            self.y -= self.speed
        elif direction == "down":
            self.y += self.speed
        elif direction == "left":
            self.x -= self.speed
            reverse = True
        elif direction == "right":
            self.x += self.speed
            reverse = False
        else:
            raise ValueError(f"Invalid direction: {direction}")

        # Check collision
        for collision in self.get_collision():
            if collision[1] == "up":
                self.y = y
            elif collision[1] == "down":
                self.y = y
            elif collision[1] == "left":
                self.x = x
            elif collision[1] == "right":
                self.x = x

        return {"animation": "run", "reverse": reverse}

    def get_collision(self) -> List[Tuple]:
        """Get the list of entities the character is colliding with.

        Returns:
            List[Tuple]: The list of entities the character is colliding with.
        """
        # Get entities
        entities = self.entity_manager.get_tangible_entities()
        ## Remove self
        entities.remove(self)

        # Get collision
        collision = pygame.sprite.spritecollide(
            self, entities, False, pygame.sprite.collide_rect
        )

        # Get collision direction
        collision = [
            (entity, self.__get_collision_direction(entity)) for entity in collision
        ]

        return collision

    def __get_collision_direction(self, entity: Entity) -> str:
        """Get the direction of the collision with the given entity.

        Args:
            entity (Entity): The entity to check the collision with.

        Returns:
            str: The direction of the collision.
        """
        # Get collision
        collision = pygame.sprite.collide_rect(self, entity)

        # Get collision direction
        if collision:
            if (
                self.rect.bottom >= entity.rect.top
                and self.rect.bottom <= entity.rect.bottom
            ):
                return "up"
            elif (
                self.rect.top <= entity.rect.bottom and self.rect.top >= entity.rect.top
            ):
                return "down"
            elif (
                self.rect.right >= entity.rect.left
                and self.rect.right <= entity.rect.right
            ):
                return "left"
            elif (
                self.rect.left <= entity.rect.right
                and self.rect.left >= entity.rect.left
            ):
                return "right"
            else:
                raise ValueError("Invalid collision")
        else:
            return None
