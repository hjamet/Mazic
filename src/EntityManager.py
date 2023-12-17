import pygame
import numpy as np
from Logger import Logger
from AssetManager import asset_manager, Asset
from typing import List, Tuple


class EntityManager:
    def __init__(self) -> None:
        self.entities = []  # List of entities
        self.events = []  # List of events to be processed by the entities
        self.next_events = []  # List of events newly created by the entities
        self.logger = Logger(self.__class__.__name__)  # Logger
        self.camera_id = None  # The id of the camera entity

    def add(self, entity_instance: object, kwargs: dict = {}) -> int:
        """Adds an entity to the game.

        Args:
            entity (object): An instance of the entity to add.

        Returns:
            int: The id of the entity.
        """
        # Spawn entity
        entity_instance.spawn()

        # Add entity to the list of entities
        ## Add AnimatedEntity in order of their camera_lvl
        entity_index = 0
        if isinstance(entity_instance, AnimatedEntity):
            while entity_index < len(self.entities) and (
                not isinstance(self.entities[entity_index], AnimatedEntity)
                or self.entities[entity_index].camera_lvl < entity_instance.camera_lvl
            ):
                entity_index += 1

        # Check if entity is a camera
        if (
            hasattr(entity_instance, "class_name")
            and entity_instance.class_name == "Camera"
        ):
            self.camera_id = entity_instance.id

        self.entities.insert(entity_index, entity_instance)
        return entity_instance.id

    def remove(self, entity: object) -> None:
        """Removes an entity from the game.

        Args:
            entity (object): The entity to remove.
        """
        if entity in self.entities:
            self.entities.remove(entity)
        else:
            self.logger.warning(f"Entity {entity} not found.")

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

    def get_camera(self):
        """Returns the camera entity.

        Returns:
            object: The camera entity.
        """
        if self.camera_id is None:
            raise ValueError("No camera found.")
        return self.get_entities(self.camera_id)[0]

    def __call__(self, external_events: list = []) -> None:
        """Update all entities.

        Args:
            external_events (list, optional): The events to add to the events list. Defaults to [].

        Returns:
            self: The instance itself.
        """
        # Add external events to the events list
        self.events += external_events

        for entity in self.entities.copy():
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

    def __init__(self, log_initialization: bool = False) -> None:
        """A base class for all entities in the game.

        Args:
            log_initialization (bool, optional): Whether to log the initialization of the entity. Defaults to False.
        """
        # Instantiates Logger
        self.logger = Logger(
            f"{self.__class__.__name__}_unspawned",
            log_initialization=log_initialization,
        )
        self.id = -1  # Unspawned entity

    def spawn(self, log_spawning: bool = True) -> None:
        """This method is intended to be used only once by the EntityManager.
        It adds the entity to the world and makes it "alive".
        Before being called, the entity does not exist in the world.

        Args:
            log_spawning (bool, optional): Whether to log the spawning of the entity. Defaults to True.
        """
        self.id = self.entity_manager.get_free_id()

        # Update logger
        self.logger.name = f"{self.__class__.__name__}_{self.id}"
        if log_spawning:
            self.logger.info(f"Entity spawned with id {self.id}")

    def update(self, events: list) -> list:
        """Default update method. To be overridden by child classes.
        This should be called every frame to update the entity state.

        Args:
            events (list): The events to be processed by the entity.

        Returns:
            list: The new events to be processed by the EntityManager.
        """
        pass

    def __call__(self, events: list) -> None:
        """Update the entity.

        Args:
            events (list): The events to be processed by the entity.

        Returns:
            self: The instance itself.
        """
        # Select events targeting the entity
        entity_events = [event for event in events if self.id in event.targets_id]

        # Process events and get new ones
        new_events = self.update(entity_events)
        if new_events is None:
            new_events = []
        self.entity_manager.next_events.extend(new_events)


class AnimatedEntity(pygame.sprite.Sprite):
    """A class for the visible objects in the game.
    Manages the display and animations. Also eventually has a hitbox and a mask."""

    asset_manager = asset_manager

    def __init__(
        self, camera_lvl: int = 0, has_hitbox: bool = False, has_mask: bool = False
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
        self.has_hitbox = has_hitbox
        self.has_mask = has_mask

        # Set private attributes
        self._is_visible = True

        # Check if child class has assets_needed
        if not hasattr(self, "assets_needed"):
            raise NotImplementedError(
                f"{self.__class__.__name__} must have assets_needed attribute."
            )

        # Load animations
        self.animations = {
            animation_type: [
                Asset(asset_name=asset_name)
                if isinstance(asset_name, str)
                else Asset(asset_surface=asset_name)
                for asset_name in assets_name
            ]
            for animation_type, assets_name in self.assets_needed.items()
        }

        # Set hitbox
        self.rect = None
        self.mask = None
        if has_hitbox and not has_mask:
            # Create simple rectangle hitbox
            self.rect = self.animations["idle"][0].get_image().get_rect()

        if has_hitbox and has_mask:
            # Create a pixel perfect hitbox
            self.mask = pygame.mask.from_surface(self.animations["idle"][0].get_image())
            self.rect = self.mask.get_rect()

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
        # Check if entity is visible
        if (
            self._is_visible is False
            or self.animations[self.current_animation_type] == []
        ):
            return None

        current_asset = self.animations[self.current_animation_type][
            int(self.current_animation_index)
        ]

        # Check if there is an image to display
        if current_asset is None:
            return None

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

    def create_animation(self, animation: str, assets: list):
        """Create an animation by adding it to the animations dictionary
        NOTE : This method can replace an already existing animation

        Args:
            animation (str): The name of the animation
            assets (list): The list of assets to use for the animation. Can be either strings or surfaces.
        """
        self.animations[animation] = [
            Asset(asset_name=asset_name)
            if isinstance(asset_name, str)
            else Asset(asset_surface=asset_name)
            for asset_name in assets
        ]

    def set_animation(
        self,
        animation: str,
        reverse: bool = False,
        size: float = 1,
        rotation: int = 0,
    ):
        """Changes the current animation of the entity

        Args:
            animation (str): The name of the animation to use.
            reverse (bool, optional): Whether the animation should be reversed. Defaults to False.
            size (float, optional): The size of the animation. Defaults to 1.
            rotation (int, optional): The rotation of the animation. Defaults to 0.

        Returns:
            self: The instance itself.
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
        if self.has_hitbox is False:
            return []

        # Get entities
        entities = self.entity_manager.get_tangible_entities()
        ## Remove self
        if self in entities:
            entities.remove(self)

        # Get collisions
        collisions = pygame.sprite.spritecollide(
            self, entities, False, pygame.sprite.collide_mask
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

    def get_closest_ennemy(self):
        """Get the closest animated entity with a hitbox.

        Returns:
            Entity: The closest ennemy
        """
        # Get entities
        entities = self.entity_manager.get_tangible_entities()
        ## Remove entities in the same team and entities without health and invisible entities
        for entity in entities:
            if (
                entity.team == self.team
                or entity.id == self.id
                or not hasattr(entity, "health_bar")
                or not entity.is_visible
            ):
                entities.remove(entity)

        # Get closest ennemi
        return (
            min(
                entities,
                key=lambda entity: np.sqrt(
                    (self.x - entity.x) ** 2 + (self.y - entity.y) ** 2
                ),
            )
            if entities != []
            else None
        )


class Event:
    def __init__(self, targets_id: list, type: str, data: dict = {}) -> None:
        """A class for representing all the events in the game.

        Args:
            targets_id (list): The list of ids of the entities targeted by the event.
            type (str): The type of event. Can be "move", "auto_attack", "damage", etc.
            data (dict, optional): La liste des informations permettant la réalisation de l'évènement. Defaults to {}.
        """
        self.targets_id = targets_id
        self.type = type
        self.data = data

        # Transform class into ids
        index = 0
        while index < len(self.targets_id):
            if not (isinstance(self.targets_id[index], int)):
                for entity in self.entity_manager.entities:
                    if entity == self.targets_id[index]:
                        self.targets_id.append(entity.id)
                self.targets_id.pop(index)

            else:
                index += 1
