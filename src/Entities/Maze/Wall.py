from EntityManager import Entity, AnimatedEntity


class Wall(Entity, AnimatedEntity):
    """A collisionless element that makes up the floor of the labyrinth."""

    assets_needed = {"idle": ["wall_mid"]}

    def __init__(self, x: int, y: int) -> None:
        """A class to represent a floor.

        Args:
            x (int): The x coordinate of the floor.
            y (int): The y coordinate of the floor.
        """
        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(self, camera_lvl=1, has_hitbox=True, has_mask=False, block_vision=True, is_tangible=True)

        # Set attributes
        self.x = x
        self.y = y
