import pygame
from Logger import Logger
import EntityManager
from Character import Character


class Mazic:
    # Sets the entity manager
    entity_manager = EntityManager.entity_manager

    def __init__(self) -> None:
        # Instantiate Logger
        self.logger = Logger(self.__class__.__name__)

        # Instantiate pygame
        pygame.init()

        # Create the display
        self.screen = pygame.display.set_mode((1200, 1000))
        ## Set window title
        pygame.display.set_caption("Mazic")
        ## Set window icon
        self.icon = pygame.image.load("assets/frames/big_demon_idle_anim_f1.png")
        pygame.display.set_icon(self.icon)

        # Instantiate attributes
        self.clock = pygame.time.Clock()
        self.running = True

        # Spawn initial entities
        self.spawn_initial_entities()

    def spawn_initial_entities(self) -> None:
        """Spawns the initial entities."""
        self.entity_manager.add(Character, {"name": "Alice"})
        self.entity_manager.add(Character, {"name": "Bob"})

    def run(self) -> None:
        # Game loop
        while self.running:
            self.clock.tick(60)
            self.events()

    def events(self) -> None:
        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
