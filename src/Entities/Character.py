import pygame
import numpy as np
from EntityManager import Entity, AnimatedEntity
from Entities.Projectile import Projectile
from EntityPlugins.Health import Health
from EntityPlugins.AbilityManager import AbilityManager


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
    ) -> None:
        """A class for the players character.

        Args:
            name (str): The name of the character.
            x (int): The x position of the character. Defaults to 0.
            y (int): The y position of the character. Defaults to 0.
            team (int): The team of the character. Defaults to None (hurt all).
        """

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=2, has_hitbox=True, has_mask=True)
        Health.__init__(self, max_hp=100)
        AbilityManager.__init__(self, entity_manager=self.entity_manager)

        # Set attributes
        self.name = name
        self.x = x
        self.y = y
        self.team = team

        # Set default attributes
        self.speed = 2
        self.add_ability("auto_attack", Projectile)

        # Set internal attributes
        self.last_auto_attack = 0

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
        self.__vision()

        return []

    def __auto_attack(self, x_click: int, y_click: int) -> None:
        # Launch projectile
        self.use_ability(
            name="auto_attack",
            kwargs={
                "x": self.x,
                "y": self.y,
                "target_x": x_click + self.x,
                "target_y": y_click + self.y,
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
        camera_zoom = self.entity_manager.get_camera().zoom
        x_mouse, y_mouse = (
            (mouse_pos[0] - window_width // 2) * camera_zoom,
            (mouse_pos[1] - window_height // 2) * camera_zoom,
        )

        # Get mouse relative position in the world
        x_mouse += self.x
        y_mouse += self.y

        # Calculate angle and distance
        basic_angle = (
            np.arctan2(y_mouse - self.y, x_mouse - self.x) if x_mouse != self.x else 0
        )
        distance = np.sqrt((x_mouse - self.x) ** 2 + (y_mouse - self.y) ** 2)

        # Calculate vision line
        ANGLE = np.pi / 4
        vision_line_nbr = (int(distance) + 1) * 2 + 1
        for i in range(vision_line_nbr):
            angle = basic_angle + ANGLE * (i - vision_line_nbr // 2)
            vision_line = (
                self.x,
                self.y,
                self.x + np.cos(angle) * distance,
                self.y + np.sin(angle) * distance,
            )

            # Get entities in vision line
            entities = self.entity_manager.get_entities_near_line(*vision_line)

            # Make entities visible until a hitbox is found
            for entity in entities:
                entity.is_visible = True
                if entity.has_hitbox:
                    break
