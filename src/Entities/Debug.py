"""Ce fichier contient une classe permettant de debugger l'affichage des entitées. Elle n'est pas véritablement utilisé dans le jeu, mais aide à son développement."""
from EntityManager import Entity, AnimatedEntity
import pygame

class Point(Entity, AnimatedEntity):
    """Un simple point rouge pour indiquer un emplacement dans l'espace."""
    
    surface = pygame.Surface((3, 3))
    surface.fill((255, 0, 0))
    pygame.draw.circle(surface, (255, 255, 255), (1, 1), 1)
    assets_needed = {"idle": [surface]}
    
    def __init__(self, x: int, y: int) -> None:
        """Un point rouge pour indiquer un emplacement dans l'espace.
        
        Args:
            x (int): La coordonnée x du point.
            y (int): La coordonnée y du point.
        """
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=9999, has_hitbox=False, has_mask=False, block_vision=False, is_tangible=False)
        
        # Set attributes
        self.x = x
        self.y = y
        
    def update(self, events : list):
        self.entity_manager.remove(self)
    