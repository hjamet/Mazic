import pygame


class Config:
    """A class for the game configuration.

    Attributes:
        key_map (dict): The key map for the game.
    """

    key_map = {
        "up": [pygame.K_UP, pygame.K_z],
        "down": [pygame.K_DOWN, pygame.K_s],
        "left": [pygame.K_LEFT, pygame.K_q],
        "right": [pygame.K_RIGHT, pygame.K_d],
    }
    fps = 60
