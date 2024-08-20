from EntityManager import Entity, AnimatedEntity


class Floor(Entity, AnimatedEntity):
    """A collisionless element that makes up the floor of the labyrinth."""

    assets_needed = {"idle": ["floor_1"]}

    def __init__(self, x: int, y: int, assets_needed: dict = None):
        """A class to represent a floor.

        Args:
            x (int): The x coordinate of the floor.
            y (int): The y coordinate of the floor.
            assets_needed (dict, optional): The assets needed to create the floor. Defaults to None.
        """
        # Set assets needed
        if assets_needed is not None:
            self.assets_needed = assets_needed

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(
            self,
            camera_lvl=1,
            has_hitbox=False,
            has_mask=False,
            block_vision=False,
            is_tangible=False,
        )

        # Set attributes
        self.x = x
        self.y = y
