import time

import pygame

# Instantiate pygame
pygame.init()

import logging

import EntityManager
from Camera import Camera
from Entities.Character import Character
from Logger import Logger

# Test
from MazeGenerator.MazeManager import MazeManager
from MazeGenerator.FogOfWar import FogOfWar
from UI.HUD import HUD
from Audio.SoundManager import SoundManager
from Entities.Monster import Monster, transform_into_immortal_monster


class Mazic:
    # Sets the entity manager
    entity_manager = EntityManager.entity_manager

    # Sets the config
    config = EntityManager.config

    # Sets the logger
    log_level = config.log_level
    logging.basicConfig(level=log_level)

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

        # Fog of War, HUD, and Audio SoundManager
        self.fog_of_war = FogOfWar()
        self.hud = HUD()
        self.sound_manager = SoundManager()

        # Spawn initial entities
        self.camera = None  # Will be set in spawn_initial_entities
        self.main_character_id = None  # Will be set in spawn_initial_entities
        self.spawn_initial_entities()

        # Store external events state
        self.key_pressed = []

    def spawn_initial_entities(self) -> None:
        """Spawns the initial entities."""

        # Spawn main character
        self.main_character = Character(
            name="Alice", is_main_character=True, x=-32, y=32
        )
        self.main_character_id = self.entity_manager.add(
            self.main_character,
        )

        # Spawn Another character
        another_character = Character(
            name="Bob",
            x=100,
            y=100,
        )
        self.entity_manager.add(another_character)

        # Spawn room
        self.maze_manager = MazeManager(self.entity_manager, 1)

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
            # Refresh Maze entities
            if (time.time() - self.start_time) % 1 < 2 / (self.config.fps):
                load_anload_entities = self.maze_manager.load_unload_rooms(
                    self.main_character
                )
                for entity in load_anload_entities.to_load:
                    self.entity_manager.add(entity)
                for entity in load_anload_entities.to_unload:
                    self.entity_manager.remove(entity)

            # Capture events
            external_events = self.events()

            # Update entities
            self.entity_manager(external_events=external_events)

            # Update display (this will also update hitboxes and masks)
            self.camera.update()

            # Update Fog of War
            all_walls = {
                (int(e.x // 16), int(e.y // 16))
                for room in getattr(self.maze_manager, "rooms", [])
                for e in room.entities
                if getattr(e, "block_vision", False)
            }
            arcane_active = getattr(
                getattr(self.main_character, "spellbook", None),
                "is_arcane_sight_active",
                False,
            )
            self.fog_of_war.update(
                self.main_character.x,
                self.main_character.y,
                all_walls,
                arcane_sight_active=arcane_active,
            )

            # Render HUD (HP, Mana, Spells, Status, Minimap)
            self.hud.render(
                self.screen,
                self.main_character,
                self.fog_of_war,
                self.maze_manager,
            )

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
                            "x_click": self.camera.x
                            + (x_click - self.config.window_width / 2)
                            / self.camera.zoom,
                            "y_click": self.camera.y
                            + (y_click - self.config.window_height / 2)
                            / self.camera.zoom,
                        },
                    )
                )

            # ---------------------------- CAPTURE SPELL CASTING --------------------------- #
            elif key in (pygame.K_1, pygame.K_KP1):
                # Spell 1: Fireball
                x_click, y_click = pygame.mouse.get_pos()
                tx = self.camera.x + (x_click - self.config.window_width / 2) / self.camera.zoom
                ty = self.camera.y + (y_click - self.config.window_height / 2) / self.camera.zoom
                if self.main_character.spellbook.cast_fireball(
                    (self.main_character.x, self.main_character.y), (tx, ty)
                ):
                    self.sound_manager.play_fireball()
                    in_game_events.append(
                        EntityManager.Event(
                            targets_id=[self.main_character_id],
                            type="auto_attack",
                            data={"x_click": tx, "y_click": ty},
                        )
                    )
            elif key in (pygame.K_2, pygame.K_KP2):
                # Spell 2: Wall Alter
                x_click, y_click = pygame.mouse.get_pos()
                tx = self.camera.x + (x_click - self.config.window_width / 2) / self.camera.zoom
                ty = self.camera.y + (y_click - self.config.window_height / 2) / self.camera.zoom
                gx, gy = int(tx // 16), int(ty // 16)
                walls_set = {
                    (int(e.x // 16), int(e.y // 16))
                    for r in getattr(self.maze_manager, "rooms", [])
                    for e in r.entities
                    if getattr(e, "block_vision", False)
                }
                floors_set = {
                    (int(e.x // 16), int(e.y // 16))
                    for r in getattr(self.maze_manager, "rooms", [])
                    for e in r.entities
                    if not getattr(e, "block_vision", False)
                }
                res = self.main_character.spellbook.cast_wall_alter(gx, gy, walls_set, floors_set)
                if res:
                    self.sound_manager.play_wall_alter()
            elif key in (pygame.K_3, pygame.K_KP3):
                # Spell 3: Arcane Sight
                if self.main_character.spellbook.cast_arcane_sight(duration=6.0):
                    self.sound_manager.play_arcane_sight()
            elif key in (pygame.K_4, pygame.K_KP4):
                # Spell 4: Blink
                x_click, y_click = pygame.mouse.get_pos()
                tx = self.camera.x + (x_click - self.config.window_width / 2) / self.camera.zoom
                ty = self.camera.y + (y_click - self.config.window_height / 2) / self.camera.zoom
                walls_set = {
                    (int(e.x // 16), int(e.y // 16))
                    for r in getattr(self.maze_manager, "rooms", [])
                    for e in r.entities
                    if getattr(e, "block_vision", False)
                }
                floors_set = {
                    (int(e.x // 16), int(e.y // 16))
                    for r in getattr(self.maze_manager, "rooms", [])
                    for e in r.entities
                    if not getattr(e, "block_vision", False)
                }
                new_pos = self.main_character.spellbook.cast_blink(
                    (self.main_character.x, self.main_character.y),
                    (tx, ty),
                    walls_set,
                    floors_set,
                )
                if new_pos:
                    self.main_character.x, self.main_character.y = new_pos
                    self.sound_manager.play_blink()

        return in_game_events
