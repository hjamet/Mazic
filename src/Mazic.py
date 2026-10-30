import time

import pygame

# Instantiate pygame
pygame.init()

import logging

import math
from typing import Tuple, Optional, Set, Dict, Any, List

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
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from EntityPlugins.SpellBook import SpellBook


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
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                pass
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
        self.monsters = []
        self.rival_mages = []
        self.active_fireballs = []
        self._spawned_monster_rooms = set()

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

        # Spawn initial Guardian Demon on valid floor or offset
        demon_x = self.main_character.x + 64
        demon_y = self.main_character.y
        if self.maze_manager.rooms:
            start_room = self.maze_manager.rooms[0]
            self._spawned_monster_rooms.add(start_room)
            floor_tiles = [
                e for e in start_room.entities
                if isinstance(e, Floor) and math.hypot(e.x - self.main_character.x, e.y - self.main_character.y) >= 32
            ]
            if floor_tiles:
                demon_x, demon_y = floor_tiles[0].x, floor_tiles[0].y

        guardian = Monster(
            name="Guardian Demon",
            x=demon_x,
            y=demon_y,
            max_hp=50,
            speed=1.4,
            damage_amount=20,
        )
        self.monsters.append(guardian)
        self.entity_manager.add(guardian)

        # Spawn Rival Mage
        rival = Character(
            name="Rival Mage",
            x=self.main_character.x - 48,
            y=self.main_character.y,
            team=3,
        )
        self.rival_mages.append(rival)
        self.entity_manager.add(rival)

    def apply_wall_alter(self, gx: int, gy: int) -> Optional[str]:
        """Applies physical wall alteration (destruction into floor or creation of wall)."""
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
        if not res:
            return None

        # Identify target room containing (gx, gy)
        target_room = None
        for r in getattr(self.maze_manager, "rooms", []):
            for e in r.entities:
                if int(e.x // 16) == gx and int(e.y // 16) == gy:
                    target_room = r
                    break
            if target_room is not None:
                break
        if target_room is None and getattr(self.maze_manager, "rooms", []):
            target_room = self.maze_manager.rooms[0]

        if res in ("DESTROYED_WALL", "destroyed"):
            for r in getattr(self.maze_manager, "rooms", []):
                to_remove = [
                    e for e in r.entities
                    if int(e.x // 16) == gx and int(e.y // 16) == gy and getattr(e, "block_vision", False)
                ]
                for e in to_remove:
                    r.entities.remove(e)
                    self.entity_manager.remove(e)

            has_floor = any(
                isinstance(e, Floor) and int(e.x // 16) == gx and int(e.y // 16) == gy
                for r in getattr(self.maze_manager, "rooms", [])
                for e in r.entities
            )
            if not has_floor and target_room is not None:
                new_floor = Floor(x=gx * 16, y=gy * 16)
                target_room.entities.append(new_floor)
                self.entity_manager.add(new_floor)

            self.sound_manager.play_wall_alter()
            return res

        elif res in ("CREATED_WALL", "created"):
            for r in getattr(self.maze_manager, "rooms", []):
                to_remove = [
                    e for e in r.entities
                    if int(e.x // 16) == gx and int(e.y // 16) == gy and not getattr(e, "block_vision", False)
                ]
                for e in to_remove:
                    r.entities.remove(e)
                    self.entity_manager.remove(e)

            if target_room is not None:
                new_wall = Wall(x=gx * 16, y=gy * 16, assets_needed={"idle": ["wall_mid"]})
                target_room.entities.append(new_wall)
                self.entity_manager.add(new_wall)

            self.sound_manager.play_wall_alter()
            return res

        return res

    def cast_player_fireball(self, target_xy: Tuple[float, float]) -> bool:
        """Casts a fireball towards target_xy, creating an active projectile."""
        fb = self.main_character.spellbook.cast_fireball(
            (self.main_character.x, self.main_character.y), target_xy
        )
        if fb is not None:
            dx = target_xy[0] - self.main_character.x
            dy = target_xy[1] - self.main_character.y
            norm = math.hypot(dx, dy)
            if norm > 0:
                dx /= norm
                dy /= norm
            else:
                dx, dy = 1.0, 0.0
            fb_data = {
                "x": float(self.main_character.x),
                "y": float(self.main_character.y),
                "dx": dx,
                "dy": dy,
                "speed": 10.0,
                "damage": fb.get("damage", 25),
            }
            self.active_fireballs.append(fb_data)
            self.sound_manager.play_fireball()
            return True
        return False

    def step_gameplay(self, dt: float, all_walls: set) -> None:
        """Runs the combat, projectile collisions and monster AI tick."""
        if hasattr(self.main_character, "spellbook") and self.main_character.spellbook is not None:
            self.main_character.spellbook.update(dt)

        # 1. Projectiles (Fireballs)
        for fb in self.active_fireballs[:]:
            fb["x"] += fb["dx"] * fb["speed"] * dt * 16
            fb["y"] += fb["dy"] * fb["speed"] * dt * 16
            tgx, tgy = int(fb["x"] // 16), int(fb["y"] // 16)

            if (tgx, tgy) in all_walls:
                if fb in self.active_fireballs:
                    self.active_fireballs.remove(fb)
                continue

            for m in self.monsters[:]:
                if math.hypot(m.x - fb["x"], m.y - fb["y"]) < 16:
                    m.damage(fb["damage"])
                    if fb in self.active_fireballs:
                        self.active_fireballs.remove(fb)

                    if m.hp <= 0:
                        if m in self.monsters:
                            self.monsters.remove(m)
                        self.entity_manager.remove(m)
                        self.main_character.spellbook.collect_crystal()
                    break

        # 2. Monsters AI & Attacks
        for m in self.monsters[:]:
            if getattr(m, "_attack_cd", 0.0) > 0:
                m._attack_cd = max(0.0, m._attack_cd - dt)

            if not self.main_character.is_immortal_monster:
                m.update_ai(dt, (self.main_character.x, self.main_character.y), all_walls)

            dist_to_player = math.hypot(m.x - self.main_character.x, m.y - self.main_character.y)
            if dist_to_player < 14 and getattr(m, "_attack_cd", 0.0) <= 0.0:
                m._attack_cd = 1.0
                was_immortal = self.main_character.is_immortal_monster
                self.main_character.damage(m.damage_amount)
                if not was_immortal and self.main_character.is_immortal_monster:
                    self.sound_manager.play_transformation()

        # 3. Immortal Monster hunts rival mages
        if self.main_character.is_immortal_monster:
            for rival in self.rival_mages[:]:
                if math.hypot(rival.x - self.main_character.x, rival.y - self.main_character.y) < 16:
                    rival.damage(9999)
                    if rival in self.rival_mages:
                        self.rival_mages.remove(rival)
                    self.entity_manager.remove(rival)
                    self.main_character.hunters_slain = getattr(self.main_character, "hunters_slain", 0) + 1

    def run(self) -> None:
        """Runs the game loop.

        This method will start an infinite loop constantly updating the game state, looking for events and updating the display.
        """
        # Game loop
        while self.running:
            dt = self.clock.tick(self.config.fps) / 1000.0
            if dt <= 0:
                dt = 1.0 / self.config.fps

            # Log FPS every 1 second
            if (time.time() - self.start_time) % 1 < 2 / (self.config.fps):
                print(f"FPS: {self.clock.get_fps()}")
            # Refresh Maze entities and spawn monsters
            if (time.time() - self.start_time) % 1 < 2 / (self.config.fps):
                load_anload_entities = self.maze_manager.load_unload_rooms(
                    self.main_character
                )
                for entity in load_anload_entities.to_load:
                    self.entity_manager.add(entity)
                for entity in load_anload_entities.to_unload:
                    self.entity_manager.remove(entity)

                for room in getattr(self.maze_manager, "rooms", []):
                    if room not in self._spawned_monster_rooms:
                        self._spawned_monster_rooms.add(room)
                        floors = [e for e in room.entities if isinstance(e, Floor)]
                        if floors:
                            spawn_floor = floors[len(floors) // 2]
                            m = Monster(
                                name=f"Demon_{room.room_nbr}",
                                x=spawn_floor.x,
                                y=spawn_floor.y,
                                max_hp=40,
                                speed=1.2,
                                damage_amount=15,
                            )
                            self.monsters.append(m)
                            self.entity_manager.add(m)

            # Capture events
            external_events = self.events()

            # Update entities
            self.entity_manager(external_events=external_events)

            # Update display (this will also update hitboxes and masks)
            self.camera.update()

            # Render active fireballs
            for fb in self.active_fireballs:
                fb_screen_x = int(
                    (fb["x"] * self.camera.zoom - self.camera.x * self.camera.zoom)
                    + self.screen.get_width() / 2
                )
                fb_screen_y = int(
                    (fb["y"] * self.camera.zoom - self.camera.y * self.camera.zoom)
                    + self.screen.get_height() / 2
                )
                pygame.draw.circle(
                    self.screen,
                    (255, 140, 20),
                    (fb_screen_x, fb_screen_y),
                    max(2, int(4 * self.camera.zoom / 5)),
                )

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

            # Step combat and AI gameplay loop
            self.step_gameplay(dt, all_walls)

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
                self.cast_player_fireball((tx, ty))
            elif key in (pygame.K_2, pygame.K_KP2):
                # Spell 2: Wall Alter
                x_click, y_click = pygame.mouse.get_pos()
                tx = self.camera.x + (x_click - self.config.window_width / 2) / self.camera.zoom
                ty = self.camera.y + (y_click - self.config.window_height / 2) / self.camera.zoom
                gx, gy = int(tx // 16), int(ty // 16)
                self.apply_wall_alter(gx, gy)
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
