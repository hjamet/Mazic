import pygame
from Logger import Logger


class EntityManager:
    def __init__(self) -> None:
        self.entities = []
        self.logger = Logger(self.__class__.__name__)
        self.logger.info("Instantiated")

        # Asset loading
        self.asset = {}

    def add(self, entity: object, kwargs: dict = {}) -> None:
        # Create entity instance
        entity_instance = entity(**kwargs)
        self.entities.append(entity_instance)

    def get_free_id(self):
        return max(self.entities, key=lambda x: x.id).id + 1 if self.entities else 0

    def load_asset(self, name: str) -> None:
        """Return an asset from the assets folder.

        Args:
            name (str): The name of the asset.

        Returns:
            pygame.Surface: The asset.
        """
        if name in self.asset:
            return self.asset[name]

        self.asset[name] = pygame.image.load(f"assets/frames/{name}.png")
        return self.asset[name]


# Instantiates the EntityManager
entity_manager = EntityManager()


class Entity:
    # Sets the entity manager
    entity_manager = entity_manager

    def __init__(self) -> None:
        """A base class for all entities in the game."""
        self.id = self.entity_manager.get_free_id()

        # Instantiates Logger
        self.logger = Logger(f"{self.__class__.__name__}_{self.id}")


class AnimatedEntity(pygame.sprite.Sprite):
    def __init__(self) -> None:
        """A class for the visible objects in the game.
        Manages the display and animations.
        """

        # Check if child class has assets_needed
        if not hasattr(self, "assets_needed"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must have assets_needed attribute."
            )

        # Load assets
        self.animations = {}
        for asset_type, assets in self.assets_needed.items():
            self.animations[asset_type] = []
            for asset in assets:
                self.animations[asset_type].append(
                    self.entity_manager.load_asset(asset)
                )

        # Set hitbox
        self.hitbox = self.animations["idle"][0].get_rect()
