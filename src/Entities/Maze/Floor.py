from EntityManager import Entity, AnimatedEntity


class Floor(Entity, AnimatedEntity):
    """A collisionless element that makes up the floor of the labyrinth."""

    assets_needed = {"idle": ["floor_1"]}

    def __init__(self, x: int, y: int, log_initialization: bool = True) -> None:
        """A class to represent a floor.

        Args:
            x (int): The x coordinate of the floor.
            y (int): The y coordinate of the floor.
            log_initialization (bool): Whether to log the initialization of the entity.
        """
        # Call parent constructors
        Entity.__init__(self, log_initialization=log_initialization)
        AnimatedEntity.__init__(
            self,
            camera_lvl=1,
            has_hitbox=True,
            has_mask=False,
            block_vision=False,
            is_tangible=False,
        )

        # Set attributes
        self.x = x
        self.y = y
