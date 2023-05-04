import time

import pygame

# Instantiate pygame
pygame.init()

import EntityManager
from Camera import Camera
from Config import Config
from Entity.Character import Character
from Logger import Logger


class Mazic:
    # Sets the entity manager
    entity_manager = EntityManager.entity_manager

    # Sets the config
    config = Config()

    def __init__(self) -> None:
        # Instantiate Logger
        self.logger = Logger(self.__class__.__name__)

        # Set start time
        self.start_time = time.time()

        # Create the display
        self.screen = pygame.display.set_mode((1200, 1000))
        # Toggles fullscreen
        if self.config.fullscreen:
            pygame.display.toggle_fullscreen()

        ## Set window title
        pygame.display.set_caption("Mazic")
        ## Set window icon
        self.icon = pygame.image.load("assets/frames/big_demon_idle_anim_f1.png")
        pygame.display.set_icon(self.icon)

        # Instantiate attributes
        self.clock = pygame.time.Clock()
        self.running = True

        # Spawn initial entities
        self.camera = None  # Will be set in spawn_initial_entities
        self.main_character_id = None  # Will be set in spawn_initial_entities
        self.spawn_initial_entities()

        # Store external events state
        self.key_pressed = []

    def spawn_initial_entities(self) -> None:
        """Spawns the initial entities."""

        # Spawn main character
        self.main_character_id = self.entity_manager.add(
            Character, {"name": "Alice"}
        ).id

        # Spawn Another character
        self.entity_manager.add(Character, {"name": "Bob", "x": 100, "y": 100})

        # Spawn Camera
        self.camera = self.entity_manager.add(
            Camera,
            {
                "game": self,
                "entity_manager": self.entity_manager,
                "following_id": self.main_character_id,
            },
        )

    def run(self) -> None:
        # Game loop
        while self.running:
            self.clock.tick(self.config.fps)

            # Log FPS every 1 second
            if (time.time() - self.start_time) % 1 < 2 / (self.config.fps):
                self.logger.debug(f"FPS: {self.clock.get_fps()}")

            # Capture events
            external_events = self.events()

            # Update entities
            self.entity_manager(external_events=external_events)

            # Update display
            self.camera.update()
            pygame.display.flip()

    def events(self) -> None:
        """Capture external events like key presses and mouse clicks.
        Eventualy generates in-game events from them.

        Returns:
            list (Event) : The events that have been generated.
        """
        in_game_events = []

        # Event loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            # Capture key presses
            elif event.type == pygame.KEYDOWN:
                self.key_pressed.append(event.key)

            # Capture key releases
            elif event.type == pygame.KEYUP:
                self.key_pressed.remove(event.key)

        # Generate in-game events
        for key in self.key_pressed:
            # Captures movement keys
            if key in self.config.key_map["up"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "up",
                        },
                    )
                )
            elif key in self.config.key_map["down"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "down",
                        },
                    )
                )
            elif key in self.config.key_map["left"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "left",
                        },
                    )
                )
            elif key in self.config.key_map["right"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "right",
                        },
                    )
                )

        return in_game_events
