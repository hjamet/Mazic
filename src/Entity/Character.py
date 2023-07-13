from EntityManager import Entity, AnimatedEntity


class Character(Entity, AnimatedEntity):
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

    def __init__(self, name: str, x: int = 0, y: int = 0) -> None:
        """A class for the players character.

        Args:
            name (str): The name of the character.
            x (int): The x position of the character. Defaults to 0.
            y (int): The y position of the character. Defaults to 0.
        """

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=2, has_hitbox=True, has_mask=True)

        # Set attributes
        self.name = name
        self.x = x
        self.y = y

        # Set default attributes
        self.speed = 2

    def update(self, event_list: list) -> None:
        """Update the entity.

        Args:
            event_list (list): The events to process.

        Returns:
            list : The events the entity generated.
        """
        animation = {"animation": "idle", "reverse": None}
        for event in event_list:
            # Move character
            if event.type == "move":
                animation = self.__move(**event.data)

        # Update animation
        self.set_animation(**animation)

        return []

    def __move(self, direction: str) -> None:
        """Move the character in the given direction.

        Args:
            direction (str): The direction to move the character.
        """
        reverse = None

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
