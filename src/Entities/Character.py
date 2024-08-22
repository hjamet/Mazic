import pygame
import numpy as np
from EntityManager import Entity, AnimatedEntity
from Entities.Projectile import Projectile
from EntityPlugins.Health import Health
from EntityPlugins.AbilityManager import AbilityManager
from typing import List, Tuple


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
            camera_lvl=3,
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

    def __move(self, direction: str) -> dict:
        """
        Déplace le personnage dans la direction donnée en utilisant move_with_collisions.

        Args:
            direction (str): La direction dans laquelle déplacer le personnage ('up', 'down', 'left', 'right').

        Returns:
            dict: Un dictionnaire contenant l'animation à utiliser et si elle doit être inversée.
        """
        reverse = None

        # Utiliser move_with_collisions pour déplacer le personnage
        collisions = self.move_with_collisions(direction, self.speed)

        # Déterminer si l'animation doit être inversée
        if direction == "left":
            reverse = True
        elif direction == "right":
            reverse = False

        return {"animation": "run", "reverse": reverse}

    def __vision(self):
        """Detect entities in line of sight based on mouse position."""
        mouse_pos = pygame.mouse.get_pos()
        camera = self.entity_manager.get_camera()
        x_mouse, y_mouse = self._get_world_mouse_pos(mouse_pos, camera)

        vision_range = 3 * 16
        dx, dy = x_mouse - self.x, y_mouse - self.y
        norm = np.hypot(dx, dy)
        if norm != 0:
            x_ortho, y_ortho = dy / norm, -dx / norm
        else:
            x_ortho, y_ortho = 1, 0

        vision_triangles = self._create_vision_triangles(
            x_ortho, y_ortho, x_mouse, y_mouse, vision_range
        )
        entities = self.entity_manager.get_animated_entities()
        entities_centers = np.array([entity.get_center() for entity in entities])

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

        current_tick = pygame.time.get_ticks()
        for entity in entities_in_vision:
            if not self._is_entity_blocked(entity, entities_in_vision):
                entity.last_seen = current_tick

    def _get_world_mouse_pos(
        self, mouse_pos: Tuple[int, int], camera
    ) -> Tuple[float, float]:
        """Convert screen mouse position to world coordinates."""
        return (
            (mouse_pos[0] / camera.zoom)
            + camera.x
            - self.config.window_width / (2 * camera.zoom),
            (mouse_pos[1] / camera.zoom)
            + camera.y
            - self.config.window_height / (2 * camera.zoom),
        )

    def _create_vision_triangles(
        self,
        x_ortho: float,
        y_ortho: float,
        x_mouse: float,
        y_mouse: float,
        vision_range: float,
    ) -> np.ndarray:
        """Create vision triangles for the character."""
        return np.array(
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

    def _is_entity_blocked(self, entity, entities_in_vision: List) -> bool:
        """Check if the entity is blocked by any other entity."""
        return any(
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
        )


def is_in_triangle(points: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    """
    Check if points are inside a triangle using barycentric coordinates.

    Args:
        points (np.ndarray): Array of points to check (shape: Nx2).
        triangle (np.ndarray): Triangle vertices (shape: 6,).

    Returns:
        np.ndarray: Boolean array indicating if each point is in the triangle.
    """
    v0 = triangle[2:4] - triangle[0:2]
    v1 = triangle[4:6] - triangle[0:2]
    v2 = points - triangle[0:2]

    # Compute dot products
    dot00, dot01, dot11 = np.dot(v0, v0), np.dot(v0, v1), np.dot(v1, v1)
    dot02, dot12 = np.dot(v0, v2.T), np.dot(v1, v2.T)

    # Compute barycentric coordinates
    inv_denom = 1 / (dot00 * dot11 - dot01 * dot01)
    u = (dot11 * dot02 - dot01 * dot12) * inv_denom
    v = (dot00 * dot12 - dot01 * dot02) * inv_denom

    # Check if point is in triangle
    return (u >= 0) & (v >= 0) & (u + v < 1)


def line_intersects_rect(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    rx: float,
    ry: float,
    rw: float,
    rh: float,
) -> bool:
    """
    Check if a line intersects with a rectangle.

    Args:
        x1, y1 (float): Start point of the line.
        x2, y2 (float): End point of the line.
        rx, ry (float): Top-left corner of the rectangle.
        rw, rh (float): Width and height of the rectangle.

    Returns:
        bool: True if the line intersects the rectangle, False otherwise.
    """

    def ccw(ax: float, ay: float, bx: float, by: float, cx: float, cy: float) -> bool:
        return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

    def intersect(
        ax: float,
        ay: float,
        bx: float,
        by: float,
        cx: float,
        cy: float,
        dx: float,
        dy: float,
    ) -> bool:
        return ccw(ax, ay, cx, cy, dx, dy) != ccw(bx, by, cx, cy, dx, dy) and ccw(
            ax, ay, bx, by, cx, cy
        ) != ccw(ax, ay, bx, by, dx, dy)

    left, right, top, bottom = rx, rx + rw, ry, ry + rh
    edges = [
        (left, top, right, top),
        (right, top, right, bottom),
        (right, bottom, left, bottom),
        (left, bottom, left, top),
    ]
    return any(intersect(x1, y1, x2, y2, *edge) for edge in edges)
