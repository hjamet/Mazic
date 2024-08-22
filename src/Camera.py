from typing import Any

from EntityManager import Entity, EntityManager
import pygame


def get_bounding_rect(image):
    """
    Get the smallest rectangle that contains all non-transparent pixels.

    Args:
        image (pygame.Surface): The image to analyze.

    Returns:
        pygame.Rect: The bounding rectangle.
    """
    mask = pygame.mask.from_surface(image)
    return mask.get_bounding_rects()[0] if mask.count() > 0 else image.get_rect()


class Camera(Entity):
    class_name = "Camera"

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
        self.speed = 100  # The higher the speed, the slower the camera
        self.zoom = 10  # The higher the zoom, the closer the camera

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
        """
        Display the entities and update their hitboxes.
        """
        self.game.screen.fill((0, 0, 0))

        for animated_entity in self.entity_manager.get_animated_entities():
            asset = animated_entity.get_current_animation()
            if asset is None:
                continue

            asset_size = asset.get_size()

            # Vérification de la visibilité dans la caméra
            screen_x = (
                animated_entity.x * self.zoom - self.x * self.zoom
            ) + self.game.screen.get_width() / 2
            screen_y = (
                animated_entity.y * self.zoom - self.y * self.zoom
            ) + self.game.screen.get_height() / 2
            if (
                screen_x + asset_size[0] * self.zoom < 0
                or screen_x - asset_size[0] * self.zoom > self.game.screen.get_width()
                or screen_y + asset_size[1] * self.zoom < 0
                or screen_y - asset_size[1] * self.zoom > self.game.screen.get_height()
            ):
                continue

            # Gestion de la transparence
            if animated_entity.visibility_memory is not None:
                transparency = (
                    1
                    if animated_entity.last_seen is None
                    else (pygame.time.get_ticks() - animated_entity.last_seen)
                    / (1000 * animated_entity.visibility_memory)
                )
                asset.set_transparency(asset.transparency_factor + transparency)

            image = asset.get_image(scale=self.zoom)
            screen_x = int(screen_x)
            screen_y = int(screen_y)

            if animated_entity.hitbox_bounding:
                bounding_rect = get_bounding_rect(image)
                hitbox_height = int(
                    bounding_rect.height * animated_entity.hitbox_height_ratio
                )
                hitbox_width = bounding_rect.width
                new_rect = pygame.Rect(0, 0, hitbox_width, hitbox_height)
                new_rect.centerx = (
                    screen_x + bounding_rect.centerx - image.get_width() // 2
                )
                new_rect.bottom = (
                    screen_y + bounding_rect.bottom - image.get_height() // 2
                )
            else:
                hitbox_height = int(
                    image.get_height() * animated_entity.hitbox_height_ratio
                )
                hitbox_width = image.get_width()
                new_rect = pygame.Rect(0, 0, hitbox_width, hitbox_height)
                new_rect.centerx = screen_x
                new_rect.bottom = screen_y + image.get_height() // 2

            animated_entity.rect = new_rect

            # Affichage de l'image
            image_rect = image.get_rect(center=(screen_x, screen_y))
            self.game.screen.blit(image, image_rect)

            # Mise à jour du masque si nécessaire
            if animated_entity.has_mask:
                animated_entity.mask = pygame.mask.from_surface(image)

            # Debug: Affichage des contours
            if animated_entity.rect:
                pygame.draw.rect(self.game.screen, (255, 0, 0), animated_entity.rect, 1)
            pygame.draw.rect(self.game.screen, (0, 255, 0), image_rect, 1)
            pygame.draw.circle(self.game.screen, (0, 0, 255), (screen_x, screen_y), 2)
