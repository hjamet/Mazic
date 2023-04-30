from typing import Any
from Logger import Logger
from EntityManager import EntityManager, Entity


class Camera(Entity):
    def __init__(self, game: object, entity_manager: EntityManager) -> None:
        """A class allowing the display of entities."""
        # Call parent constructor
        Entity.__init__(self)

        # Set attributes
        self.game = game
        self.entity_manager = entity_manager

        # Set camera position
        self.x = 0
        self.y = 0

        # Set camera speed
        self.speed = 5

        # Indicates the entity to be followed
        self.following_id = None

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        """Update the camera position."""
        if "following_id" in kwds:
            self.following_id = kwds["following_id"]
            self.logger.info(f"Following entity {self.following_id}")
        return self

    def update(self) -> None:
        """Display the entities."""
        for animated_entity in self.entity_manager.get_animated_entities():
            self.game.screen.blit(
                animated_entity.get_current_animation(),
                (
                    animated_entity.x - self.x,
                    animated_entity.y - self.y,
                ),
            )
