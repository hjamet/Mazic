import pygame
from Logger import Logger
from AssetManager import asset_manager, Asset
from typing import List, Tuple


class EntityManager:
    def __init__(self) -> None:
        self.entities = []  # List of entities
        self.events = []  # List of events to be processed by the entities
        self.next_events = []  # List of events newly created by the entities
        self.logger = Logger(self.__class__.__name__)

    def add(self, entity: object, kwargs: dict = {}) -> None:
        """Adds an entity to the game.

        Args:
            entity (object): The entity class.
            kwargs (dict, optional): The entity attributes. Defaults to {}.

        Returns:
            int: The entity id.
        """
        # Create entity instance
        entity_instance = entity(**kwargs)

        # Add entity to the list of entities
        ## Add AnimatedEntity in order of their camera_lvl
        entity_index = 0
        if isinstance(entity_instance, AnimatedEntity):
            while entity_index < len(self.entities) and (
                self.entities[entity_index].camera_lvl < entity_instance.camera_lvl
                or not isinstance(self.entities[entity_index], AnimatedEntity)
            ):
                entity_index += 1

        self.entities.insert(entity_index, entity_instance)
        return entity_instance

    def get_free_id(self):
        return max(self.entities, key=lambda x: x.id).id + 1 if self.entities else 0

    def get_animated_entities(self):
        """Returns all animated entities.

        Returns:
            list: A list of animated entities.
        """
        return [
            entity for entity in self.entities if isinstance(entity, AnimatedEntity)
        ]

    def get_tangible_entities(self):
        """Returns all entities with a hitbox.

        Returns:
            list: A list of entities with a hitbox.
        """
        return [
            entity
            for entity in self.entities
            if hasattr(entity, "rect") and entity.rect is not None
        ]

    def get_entities(self, id: int, entity_type: object = None):
        """Returns an entity by its id.

        Args:
            id (int): The entity id.
            entity_type (object, optional): The entity type. Defaults to None.

        Returns:
            object: The entity.
        """
        if entity_type is not None:
            return [
                entity
                for entity in self.entities
                if entity.id == id and isinstance(entity, entity_type)
            ]
        elif id is not None:
            return [entity for entity in self.entities if entity.id == id]
        else:
            self.logger.error("No id or entity_type provided.")
            return []

    def __call__(self, external_events: list = []) -> None:
        """Update all entities.

        Args:
            external_events (list, optional): The events to add to the events list. Defaults to [].

        Returns:
            self: The instance itself.
        """
        # Add external events to the events list
        self.events += external_events

        for entity in self.entities:
            entity(self.events)

        self.update_events()
        return self

    def update_events(self):
        """Update the events list by deleting the events that have been processed and adding the new ones.

        Returns:
            self: The instance itself.
        """
        self.events = self.next_events
        self.next_events = []

        return self


# Instantiates the EntityManager
entity_manager = EntityManager()


class Entity:
    # Sets the entity manager
    entity_manager = entity_manager

    def __init__(self, log_initialization: bool = True) -> None:
        """A base class for all entities in the game.

        Args:
            log_initialization (bool, optional): Whether to log the initialization of the entity. Defaults to True.
        """
        self.id = self.entity_manager.get_free_id()

        # Instantiates Logger
        self.logger = Logger(
            f"{self.__class__.__name__}_{self.id}",
            log_initialization=log_initialization,
        )

    def update(self, events: list) -> list:
        """Default update method. To be overridden by child classes.
        This should be called every frame to update the entity state.

        Args:
            events (list): The events to be processed by the entity.

        Returns:
            list: The new events to be processed by the EntityManager.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must have an update method."
        )

    def __call__(self, events: list) -> None:
        """Update the entity.

        Args:
            events (list): The events to be processed by the entity.

        Returns:
            self: The instance itself.
        """
        # Select events targeting the entity
        entity_events = [event for event in events if self.id in event.targets]

        # Process events and get new ones
        new_events = self.update(entity_events)
        self.entity_manager.next_events.extend(new_events)


class AnimatedEntity(pygame.sprite.Sprite):
    asset_manager = asset_manager

    def __init__(
        self, camera_lvl: int = 0, hitbox: bool = False, mask: bool = False
    ) -> None:
        """A class for the visible objects in the game.
        Manages the display and animations.

        Args:
            camera_lvl (int, optional): The camera level. Bigger number means the entity will be displayed on top of the others. Defaults to 0.
            hitbox (bool, optional): Whether the entity has a hitbox. Defaults to False.
            mask (bool, optional): Whether the entity has a mask (for pixel perfect collision). Defaults to True.

        Raises:
            NotImplementedError: If the child class does not have an assets_needed attribute.
        """
        # Save attributes
        self.camera_lvl = camera_lvl

        # Check if child class has assets_needed
        if not hasattr(self, "assets_needed"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must have assets_needed attribute."
            )

        # Load animations
        self.animations = {
            animation_type: [Asset(asset_name) for asset_name in assets_name]
            for animation_type, assets_name in self.assets_needed.items()
        }

        # Set hitbox
        self.rect = None
        self.mask = None
        if hitbox:
            self.rect = self.animations["idle"][0].get_image().get_rect()

        if hitbox and mask:
            self.mask = pygame.mask.from_surface(self.animations["idle"][0].get_image())

        # Set current animation
        self.current_animation_type = "idle"
        self.current_animation_index = 0

        # Set current state
        self.x = 0
        self.y = 0
        self.rotation = 90
        self.size = 1
        self.reverse = False

    def get_current_animation(self):
        """Returns the current animation."""
        current_asset = self.animations[self.current_animation_type][
            int(self.current_animation_index)
        ]

        # Update current frame
        animation_speed = (
            self.animation_speed[self.current_animation_type]
            if hasattr(self, "animation_speed")
            and self.current_animation_type in self.animation_speed
            else 1
        )
        self.current_animation_index = (
            self.current_animation_index + animation_speed
        ) % len(self.animations[self.current_animation_type])

        # Rotate frame
        current_asset = current_asset.rotate(self.rotation)

        # Resize frame
        current_asset = current_asset.scale(self.size)

        # Reverse frame
        current_asset = current_asset.reverse(self.reverse)

        return current_asset

    def set_animation(
        self,
        animation: str,
        reverse: bool = False,
        size: float = 1,
        rotation: int = 0,
    ):
        """Change l'animation actuelle de l'entité

        Args:
            animation_type (str): Le type d'animation à utiliser

        Returns:
            self: L'instance elle-même.
        """
        # Set current state
        self.reverse = reverse if reverse is not None else self.reverse
        self.size = size if size is not None else self.size
        self.rotation = rotation if rotation is not None else self.rotation

        # Reset animation index if animation type changed
        if self.current_animation_type != animation:
            self.current_animation_index = 0
            self.current_animation_type = animation
        return self

    def get_collisions(self) -> List[Tuple]:
        """Get the list of entities the character is colliding with. The list is empty if the entity has no hitbox.

        Returns:
            List[Tuple]: The list of entities the character is colliding with.
        """
        # Check if entity has hitbox
        if self.rect is None:
            return []

        # Get entities
        entities = self.entity_manager.get_tangible_entities()
        ## Remove self
        entities.remove(self)

        # Get collision
        collisions = pygame.sprite.spritecollide(
            self, entities, False, pygame.sprite.collide_rect
        )

        # Get collision direction
        collisions_directions = []
        for collision in collisions:
            collisions_directions.append(
                (
                    collision,
                    collision.x - self.x,
                    collision.y - self.y,
                )
            )

        return collisions_directions


class Event:
    def __init__(self, targets: list, type: str, data: dict = {}) -> None:
        self.targets = targets
        self.type = type
        self.data = data

        # Transform class into ids
        index = 0
        while index < len(self.targets):
            if not (isinstance(self.targets[index], int)):
                for entity in self.entity_manager.entities:
                    if entity == self.targets[index]:
                        self.targets.append(entity.id)
                self.targets.pop(index)

            else:
                index += 1
