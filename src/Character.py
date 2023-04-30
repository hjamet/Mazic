import pygame
from EntityManager import Entity


class Character(Entity):
    def __init__(self, name: str) -> None:
        super().__init__()

        self.name = name
