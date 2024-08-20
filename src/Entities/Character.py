import pygame
import numpy as np
import pandas as pd
from EntityManager import Entity, AnimatedEntity
from Entities.Projectile import Projectile
from EntityPlugins.Health import Health
from EntityPlugins.AbilityManager import AbilityManager
from utils.is_in_triangle import ft_is_in_triangle
from Entities.Debug import Point


class Character(Entity, AnimatedEntity, Health, AbilityManager):
    """The main character of the game.

    Args:
        Entity (Entity): A class giving the character the ability to process events.
        AnimatedEntity (AnimatedEntity): A class giving the character the ability to be animated and displayed.

    Raises:
        ValueError: If the character name is not valid.

    Returns:
        Character: A character instance.
    """

    assets_needed = {
        "idle": [
            "wizzard_m_idle_anim_f0",
            "wizzard_m_idle_anim_f1",
            "wizzard_m_idle_anim_f2",
            "wizzard_m_idle_anim_f3",
        ],
        "run": [
            "wizzard_m_run_anim_f0",
            "wizzard_m_run_anim_f1",
            "wizzard_m_run_anim_f2",
            "wizzard_m_run_anim_f3",
        ],
        "hit": [
            "wizzard_m_hit_anim_f0",
        ],
    }

    animation_speed = {
        "idle": 0.05,
        "run": 0.2,
        "hit": 0.1,
    }

    def __init__(
        self,
        name: str,
        x: int = 0,
        y: int = 0,
        team: int = None,
        is_main_character: bool = False,
    ) -> None:
        """A class for the players character.

        Args:
            name (str): The name of the character.
            x (int): The x position of the character. Defaults to 0.
            y (int): The y position of the character. Defaults to 0.
            team (int): The team of the character. Defaults to None (hurt all).
            is_main_character (bool): Whether the character is the main character or not. Defaults to False.
        """
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(
            self,
            camera_lvl=2,
            has_hitbox=True,
            has_mask=True,
            is_tangible=True,
            hitbox_height_ratio=0.5,
        )  # Half-height hitbox
        Health.__init__(self, max_hp=100, is_main_character_health=is_main_character)
        AbilityManager.__init__(self, entity_manager=self.entity_manager)

        # Set attributes
        self.name = name
        self.x = x
        self.y = y
        self.team = team
        self.is_main_character = is_main_character

        # Set default attributes
        self.speed = 2
        self.add_ability("auto_attack", Projectile)

        # Set internal attributes
        self.last_auto_attack = 0
        if self.is_main_character:
            self.visibility_memory = None

    def update(self, event_list: list) -> None:
        """This function is called at each frame. It allows the entity to react to a list of events.

        Args:
            event_list (list): The events to process.

        Returns:
            list : The events the entity generated.
        """
        # Check for events
        animation = {"animation": "idle", "reverse": None}
        for event in event_list:
            # Move character
            if event.type == "move":
                animation = self.__move(**event.data)
            elif event.type == "auto_attack":
                self.__auto_attack(**event.data)
            elif event.type == "damage":
                self.logger.debug(
                    f"Character {self.id} took {event.data['damage']} damage"
                )
                self.damage(event.data["damage"])

        # Update animation
        self.set_animation(**animation)

        # Update vision
        if self.is_main_character:
            self.__vision()

        return []

    def __auto_attack(self, x_click: int, y_click: int) -> None:
        # Launch projectile
        self.use_ability(
            name="auto_attack",
            kwargs={
                "x": self.x,
                "y": self.y,
                "target_x": x_click,
                "target_y": y_click,
                "team": self.team,
                "launcher_id": self.id,
            },
        )

    def __move(self, direction: str) -> None:
        """Move the character in the given direction.

        Args:
            direction (str): The direction to move the character.
        """
        reverse = None

        # Set the last move time
        self.__last_move = pygame.time.get_ticks()

        # Check for collisions
        collisions = self.get_collisions()
        collisions_x = (
            max(
                [collision[1] for collision in collisions],
                key=lambda collision: abs(collision),
            )
            if collisions
            else 0
        )
        collisions_y = (
            max(
                [collision[2] for collision in collisions],
                key=lambda collision: abs(collision),
            )
            if collisions
            else 0
        )

        if direction == "up":
            if collisions_y >= 0:
                self.y -= self.speed
        elif direction == "down":
            if collisions_y <= 0:
                self.y += self.speed
        elif direction == "left":
            if collisions_x >= 0:
                self.x -= self.speed
            reverse = True
        elif direction == "right":
            if collisions_x <= 0:
                self.x += self.speed
            reverse = False
        else:
            raise ValueError(f"Invalid direction: {direction}")

        return {"animation": "run", "reverse": reverse}

    def __vision(self):
        """Detect entities in line of sight based on mouse position."""
        mouse_pos = pygame.mouse.get_pos()
        camera = self.entity_manager.get_camera()
        x_mouse, y_mouse = (
            (mouse_pos[0] / camera.zoom)
            + camera.x
            - self.config.window_width / (2 * camera.zoom),
            (mouse_pos[1] / camera.zoom)
            + camera.y
            - self.config.window_height / (2 * camera.zoom),
        )

        vision_range = 3 * 16
        dx, dy = x_mouse - self.x, y_mouse - self.y
        norm = (dx**2 + dy**2) ** 0.5
        if norm != 0:
            x_ortho, y_ortho = dy / norm, -dx / norm
        else:
            x_ortho, y_ortho = 1, 0

        vision_triangles = np.array(
            [
                [
                    self.x + x_ortho,
                    self.y + y_ortho,
                    self.x - 16 * x_ortho,
                    self.y - 16 * y_ortho,
                    x_mouse + vision_range * x_ortho,
                    y_mouse + vision_range * y_ortho,
                ],
                [
                    self.x - 16 * x_ortho,
                    self.y - 16 * y_ortho,
                    x_mouse + vision_range * x_ortho,
                    y_mouse + vision_range * y_ortho,
                    x_mouse - vision_range * x_ortho,
                    y_mouse - vision_range * y_ortho,
                ],
            ]
        )

        entities = self.entity_manager.get_animated_entities()
        entities_centers = np.array([entity.get_center() for entity in entities])

        def is_in_triangle(points, triangle):
            """Check if points are inside a triangle."""
            v0 = triangle[2:4] - triangle[0:2]
            v1 = triangle[4:6] - triangle[0:2]
            v2 = points - triangle[0:2]

            dot00 = np.dot(v0, v0)
            dot01 = np.dot(v0, v1)
            dot02 = np.dot(v0, v2.T)
            dot11 = np.dot(v1, v1)
            dot12 = np.dot(v1, v2.T)

            invDenom = 1 / (dot00 * dot11 - dot01 * dot01)
            u = (dot11 * dot02 - dot01 * dot12) * invDenom
            v = (dot00 * dot12 - dot01 * dot02) * invDenom

            return (u >= 0) & (v >= 0) & (u + v < 1)

        in_triangle = np.any(
            [
                is_in_triangle(entities_centers, triangle)
                for triangle in vision_triangles
            ],
            axis=0,
        )
        entities_in_vision = [
            entity for entity, in_triangle in zip(entities, in_triangle) if in_triangle
        ]

        def line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh):
            def ccw(ax, ay, bx, by, cx, cy):
                return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

            def intersect(ax, ay, bx, by, cx, cy, dx, dy):
                return ccw(ax, ay, cx, cy, dx, dy) != ccw(
                    bx, by, cx, cy, dx, dy
                ) and ccw(ax, ay, bx, by, cx, cy) != ccw(ax, ay, bx, by, dx, dy)

            left, right, top, bottom = rx, rx + rw, ry, ry + rh
            return any(
                intersect(x1, y1, x2, y2, *edge)
                for edge in [
                    (left, top, right, top),
                    (right, top, right, bottom),
                    (right, bottom, left, bottom),
                    (left, bottom, left, top),
                ]
            )

        current_tick = pygame.time.get_ticks()
        for entity in entities_in_vision:
            if not any(
                blocking_entity != entity
                and blocking_entity.block_vision
                and line_intersects_rect(
                    self.x,
                    self.y,
                    entity.x,
                    entity.y,
                    blocking_entity.x,
                    blocking_entity.y,
                    16,
                    16,
                )
                for blocking_entity in entities_in_vision
            ):
                entity.last_seen = current_tick
