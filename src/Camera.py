from typing import Any
from Logger import Logger
from EntityManager import EntityManager, Entity


class Camera(Entity):
    def __init__(
        self, game: object, entity_manager: EntityManager, following_id: int = None
    ) -> None:
        """A class allowing the display of entities.

        Args:
            game (object): The game instance.
            entity_manager (EntityManager): The entity manager instance.
            following_id (int): The id of the entity to follow.

        """
        # Call parent constructor
        Entity.__init__(self)

        # Set attributes
        self.game = game
        self.entity_manager = entity_manager

        # Set camera position
        self.x = 0
        self.y = 0

        # Set camera speed
        self.speed = 10  # The higher the speed, the slower the camera

        # Indicates the entity to be followed
        self.following_id = following_id

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """Update the camera position."""
        # Move to the followed entity
        if self.following_id is not None:
            entities = self.entity_manager.get_entities(id=self.following_id)
            if not entities:
                self.logger.warning(
                    f"Entity with id {self.following_id} not found. Stopping following."
                )
                self.following_id = None
            else:
                entity = entities[0]
                self.x += (entity.x - self.x) / self.speed
                self.y += (entity.y - self.y) / self.speed

        return self

    def update(self) -> None:
        """Display the entities."""
        # Fill the screen with black
        self.game.screen.fill((0, 0, 0))

        for animated_entity in self.entity_manager.get_animated_entities():
            self.game.screen.blit(
                animated_entity.get_current_animation(),
                (
                    (animated_entity.x - self.x) + self.game.screen.get_width() / 2,
                    (animated_entity.y - self.y) + self.game.screen.get_height() / 2,
                ),
            )
