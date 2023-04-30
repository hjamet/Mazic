import pygame
from Logger import Logger


class EntityManager:
    def __init__(self) -> None:
        self.entities = []  # List of entities
        self.events = []  # List of events to be processed by the entities
        self.next_events = []  # List of events newly created by the entities
        self.logger = Logger(self.__class__.__name__)

        # Asset loading
        self.asset = {}

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
        self.entities.append(entity_instance)
        return entity_instance

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

    def get_animated_entities(self):
        """Returns all animated entities.

        Returns:
            list: A list of animated entities.
        """
        return [
            entity for entity in self.entities if isinstance(entity, AnimatedEntity)
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

    def __init__(self) -> None:
        """A base class for all entities in the game."""
        self.id = self.entity_manager.get_free_id()

        # Instantiates Logger
        self.logger = Logger(f"{self.__class__.__name__}_{self.id}")

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

        # If child class is AnimatedEntity, update the hitbox
        if isinstance(self, AnimatedEntity):
            self.update_hitbox()


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
        current_frame = self.animations[self.current_animation_type][
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
        current_frame = pygame.transform.rotate(current_frame, self.rotation)

        # Resize frame
        current_frame = pygame.transform.scale(
            current_frame,
            (
                int(current_frame.get_width() * self.size),
                int(current_frame.get_height() * self.size),
            ),
        )

        # Reverse frame
        if self.reverse:
            current_frame = pygame.transform.flip(current_frame, True, False)

        return current_frame

    def update_hitbox(self):
        """Updates the hitbox."""
        self.hitbox.x = self.x
        self.hitbox.y = self.y

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
