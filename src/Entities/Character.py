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
        # Get mouse position
        mouse_pos = pygame.mouse.get_pos()

        # Get mouse relative position
        window_width, window_height = (
            self.config.window_width,
            self.config.window_height,
        )
        camera = self.entity_manager.get_camera()
        camera_zoom = camera.zoom
        camera_coords = camera.x, camera.y
        x_mouse, y_mouse = (
            mouse_pos[0] / camera_zoom,
            mouse_pos[1] / camera_zoom,
        )

        # Get mouse relative position in the world with a random offset
        x_mouse += camera_coords[0] - window_width / (2 * camera_zoom)
        y_mouse += camera_coords[1] - window_height / (2 * camera_zoom)

        self.entity_manager.add(Point(x_mouse, y_mouse))

        # Get distance to mouse
        vision_range = 3

        # Get unit orthogonal vector
        x_ortho = y_mouse - self.y
        y_ortho = -(x_mouse - self.x)
        norm = np.sqrt(x_ortho**2 + y_ortho**2)
        if norm != 0:
            x_ortho /= norm
            y_ortho /= norm
        else:
            x_ortho = 1
            y_ortho = 0

        # Define vision triangles
        vision_triangle_1 = [
            (self.x + x_ortho, self.y + y_ortho),
            (self.x - 16 * x_ortho, self.y - 16 * y_ortho),
            (
                x_mouse + vision_range * x_ortho * 16,
                y_mouse + vision_range * y_ortho * 16,
            ),
        ]
        vision_triangle_2 = [
            (self.x - 16 * x_ortho, self.y - 16 * y_ortho),
            (
                x_mouse + vision_range * x_ortho * 16,
                y_mouse + vision_range * y_ortho * 16,
            ),
            (
                x_mouse - vision_range * x_ortho * 16,
                y_mouse - vision_range * y_ortho * 16,
            ),
        ]

        # Get entities in vision triangle
        entities = self.entity_manager.get_animated_entities()
        # Debug vision
        # entities = list(filter(lambda entity: not isinstance(entity, Point), entities))
        entities_shapes = pd.DataFrame(
            [entity.get_center() for entity in entities],
        )

        in_triangle_index = pd.concat(
            [
                pd.Series(
                    ft_is_in_triangle(
                        entities_shapes,
                        *vision_triangle_1[0],
                        *vision_triangle_1[1],
                        *vision_triangle_1[2],
                    )
                ),
                pd.Series(
                    ft_is_in_triangle(
                        entities_shapes,
                        *vision_triangle_2[0],
                        *vision_triangle_2[1],
                        *vision_triangle_2[2],
                    )
                ),
            ]
        ).unique()
        entities_in_vision = [entities[i] for i in in_triangle_index]

        # Fonction pour vérifier si une ligne intersecte avec un rectangle
        def line_intersects_rect(x1, y1, x2, y2, rx, ry, rw, rh):
            """
            Vérifie si une ligne intersecte avec un rectangle.

            Args:
                x1, y1 (float): Coordonnées du point de départ de la ligne.
                x2, y2 (float): Coordonnées du point d'arrivée de la ligne.
                rx, ry (float): Coordonnées du coin supérieur gauche du rectangle.
                rw, rh (float): Largeur et hauteur du rectangle.

            Returns:
                bool: True si la ligne intersecte le rectangle, False sinon.
            """
            left = rx
            right = rx + rw
            top = ry
            bottom = ry + rh

            def ccw(ax, ay, bx, by, cx, cy):
                return (cy - ay) * (bx - ax) > (by - ay) * (cx - ax)

            def intersect(ax, ay, bx, by, cx, cy, dx, dy):
                return ccw(ax, ay, cx, cy, dx, dy) != ccw(
                    bx, by, cx, cy, dx, dy
                ) and ccw(ax, ay, bx, by, cx, cy) != ccw(ax, ay, bx, by, dx, dy)

            return (
                intersect(x1, y1, x2, y2, left, top, right, top)
                or intersect(x1, y1, x2, y2, right, top, right, bottom)
                or intersect(x1, y1, x2, y2, right, bottom, left, bottom)
                or intersect(x1, y1, x2, y2, left, bottom, left, top)
            )

        # Debug vision
        # for entity in entities_in_vision:
        #     self.entity_manager.add(Point(entity.x, entity.y, color=(0, 255, 0)))
        # for point in vision_triangle_1:
        #     self.entity_manager.add(Point(point[0], point[1], color=(0, 0, 255)))
        # for point in vision_triangle_2:
        #     self.entity_manager.add(Point(point[0], point[1], color=(0, 0, 255)))

        # Make entities visible until a hitbox is found
        current_tick = pygame.time.get_ticks()
        for entity in entities_in_vision:
            is_visible = True
            for blocking_entity in entities_in_vision:
                if blocking_entity != entity and blocking_entity.block_vision:
                    if line_intersects_rect(
                        self.x,
                        self.y,
                        entity.x,
                        entity.y,
                        blocking_entity.x,
                        blocking_entity.y,
                        16,
                        16,
                    ):
                        is_visible = False
                        break

            if is_visible:
                entity.last_seen = current_tick
