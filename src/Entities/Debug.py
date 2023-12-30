"""Ce fichier contient une classe permettant de debugger l'affichage des entitées. Elle n'est pas véritablement utilisé dans le jeu, mais aide à son développement."""
from EntityManager import Entity, AnimatedEntity
import pygame

class Point(Entity, AnimatedEntity):
    """Un simple point rouge pour indiquer un emplacement dans l'espace."""
    assets_needed = {"idle": []} # Placeholder
    
    def __init__(self, x: int, y: int, color : tuple = (255, 0, 0)) -> None:
        """Un point rouge pour indiquer un emplacement dans l'espace.
        
        Args:
            x (int): La coordonnée x du point.
            y (int): La coordonnée y du point.
            color (tuple): La couleur du point. Defaults to (255, 0, 0) (rouge)
        """
        surface = pygame.Surface((3, 3))
        surface.fill(color)
        pygame.draw.circle(surface, color, (1, 1), 1)
        self.assets_needed["idle"] = [surface]
        
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=9999, has_hitbox=False, has_mask=False, block_vision=False, is_tangible=False)
        
        # Set attributes
        self.x = x
        self.y = y
        
        # Set internal attributes
        self.visibility_memory = None
        
    def update(self, events : list):
        self.entity_manager.remove(self)
    