import time

import pygame

# Instantiate pygame
pygame.init()

import EntityManager
from Camera import Camera
from Config import Config
from Entities.Character import Character
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Logger import Logger


class Mazic:
    # Sets the entity manager
    entity_manager = EntityManager.entity_manager

    # Sets the config
    config = EntityManager.config

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
        (
            self.config.window_width,
            self.config.window_height,
        ) = pygame.display.get_surface().get_size()

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
        main_character = Character(
            name="Alice",
            is_main_character=True,
            x = 0,
            y = 32
        )
        self.main_character_id = self.entity_manager.add(
            main_character,
        )

        # Spawn Another character
        another_character = Character(
            name="Bob",
            x=100,
            y=100,
        )
        self.entity_manager.add(another_character)

        # Spawn floor
        for x in range(-10, 10):
            for y in range(-10, 10):
                if y != 0:
                    floor = Floor(x=x * 16, y=y * 16)
                    self.entity_manager.add(floor)
                else:
                    wall = Wall(x=x * 16, y=y * 16)
                    wall.is_visible = True # TODO delete this line
                    self.entity_manager.add(wall)

        # Spawn Camera
        self.camera = Camera(
            game=self,
            entity_manager=self.entity_manager,
            following_id=self.main_character_id,
        )
        self.camera_id = self.entity_manager.add(
            self.camera,
        )

    def run(self) -> None:
        """Runs the game loop.

        This method will start an infinite loop constantly updating the game state, looking for events and updating the display.
        """
        # Game loop
        while self.running:
            self.clock.tick(self.config.fps)

            # Log FPS every 1 second
            if (time.time() - self.start_time) % 1 < 2 / (self.config.fps):
                print(f"FPS: {self.clock.get_fps()}")

            # Capture events
            external_events = self.events()

            # Update entities
            self.entity_manager(external_events=external_events)

            # Update display (this will also update hitboxes and masks)
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

            # Capture mouse clicks
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Capture left click
                if event.button == pygame.BUTTON_LEFT:
                    self.key_pressed.append(event.button)
                elif event.button == pygame.BUTTON_RIGHT:
                    self.key_pressed.append(event.button)

            # Capture mouse releases
            elif event.type == pygame.MOUSEBUTTONUP:
                # Capture left click
                if event.button == pygame.BUTTON_LEFT:
                    self.key_pressed.remove(event.button)
                elif event.button == pygame.BUTTON_RIGHT:
                    self.key_pressed.remove(event.button)

        # Generate in-game events
        for key in self.key_pressed:
            # --------------------------- CAPTURE MOUVEMENT KEY -------------------------- #
            if key in self.config.key_map["up"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets_id=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "up",
                        },
                    )
                )
            elif key in self.config.key_map["down"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets_id=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "down",
                        },
                    )
                )
            elif key in self.config.key_map["left"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets_id=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "left",
                        },
                    )
                )
            elif key in self.config.key_map["right"]:
                in_game_events.append(
                    EntityManager.Event(
                        targets_id=[self.main_character_id],
                        type="move",
                        data={
                            "direction": "right",
                        },
                    )
                )

            # ---------------------------- CAPTURE AUTO ATTACK --------------------------- #
            elif key in self.config.key_map["auto_attack"]:
                x_click, y_click = pygame.mouse.get_pos()
                in_game_events.append(
                    EntityManager.Event(
                        targets_id=[self.main_character_id],
                        type="auto_attack",
                        data={
                            "x_click": self.camera.x + (x_click - self.config.window_width / 2)
                            / self.camera.zoom,
                            "y_click": self.camera.y + (y_click - self.config.window_height / 2)
                            / self.camera.zoom,
                        },
                    )
                )

        return in_game_events
