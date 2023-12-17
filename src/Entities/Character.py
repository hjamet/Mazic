import pygame
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
