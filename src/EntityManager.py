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
