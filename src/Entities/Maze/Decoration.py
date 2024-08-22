from EntityManager import Entity, AnimatedEntity


class Decoration(Entity, AnimatedEntity):
    """A collisionless element that makes up the decoration of the labyrinth."""

    assets_needed = {"idle": ["wall_top_mid"]}

    def __init__(
        self,
        x: int,
        y: int,
        assets_needed: dict = None,
        rotation: int = 0,
        reverse: bool = False,
    ):
        """
        Initialize a Decoration object.

        Args:
            x (int): The x coordinate of the decoration.
            y (int): The y coordinate of the decoration.
            assets_needed (dict, optional): The assets needed to create the decoration. Defaults to None.
            rotation (int, optional): The rotation of the decoration. Defaults to 0.
            reverse (bool, optional): Whether the decoration is reversed. Defaults to False.
        """
        # Set assets needed
        if assets_needed is not None:
            self.assets_needed = assets_needed

        # Call parent constructors
        Entity.__init__(self)
        AnimatedEntity.__init__(
            self,
            camera_lvl=4,  # Higher value to ensure it's in the foreground
            has_hitbox=False,  # Intangible
            has_mask=False,
            block_vision=False,
            is_tangible=False,
        )

        # Set attributes
        self.x = x
        self.y = y

        # Set animation
        self.set_animation("idle", rotation=rotation, reverse=reverse)
