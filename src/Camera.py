from typing import Any

from EntityManager import Entity, EntityManager
from AssetManager import asset_manager, Asset


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
        self.x = 50
        self.y = 50

        # Set camera current configuration
        self.speed = 80  # The higher the speed, the slower the camera
        self.zoom = 3  # The higher the zoom, the closer the camera

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
                self.x += (entity.x * self.zoom - self.x * self.zoom) / self.speed
                self.y += (entity.y * self.zoom - self.y * self.zoom) / self.speed

        return self

    def update(self) -> None:
        """Display the entities."""
        # Fill the screen with black
        self.game.screen.fill((0, 0, 0))

        for animated_entity in self.entity_manager.get_animated_entities():
            # Get the current animation
            asset = animated_entity.get_current_animation()

            # Get the asset size
            asset_size = asset.get_size()

            # Check if the entity is in the camera view
            if (
                animated_entity.x * self.zoom
                - self.x * self.zoom
                + self.game.screen.get_width() / 2
                + asset_size[0] * 2 * self.zoom
                < 0
                or animated_entity.x * self.zoom
                - self.x * self.zoom
                + self.game.screen.get_width() / 2
                - asset_size[0] * 2 * self.zoom
                > self.game.screen.get_width()
                or animated_entity.y * self.zoom
                - self.y * self.zoom
                + self.game.screen.get_height() / 2
                + asset_size[1] * 2 * self.zoom
                < 0
                or animated_entity.y * self.zoom
                - self.y * self.zoom
                + self.game.screen.get_height() / 2
                - asset_size[1] * 2 * self.zoom
                > self.game.screen.get_height()
            ):
                continue

            # Apply all transformations and get final image
            image = asset.get_image(
                scale=self.zoom,
            )

            self.game.screen.blit(
                image,
                (
                    int(
                        (animated_entity.x * self.zoom - self.x * self.zoom)
                        + self.game.screen.get_width() / 2
                        - image.get_width() / 2
                    ),
                    int(
                        (animated_entity.y * self.zoom - self.y * self.zoom)
                        + self.game.screen.get_height() / 2
                        - image.get_height() / 2
                    ),
                ),
            )
