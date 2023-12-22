import pygame
import os
from Config import Config
import numpy as np


class AssetManager:
    def __init__(self) -> None:
        """A class to manage the assets.
        It is optimised to load images and apply common transformations very quickly.
        """
        self.raw_asset = {}
        self.transformed_asset = {}

        # Set attributes
        self.config = Config()

    def get_image(self, asset) -> pygame.Surface:
        """Load an asset and apply transformations.

        Args:
            asset: The asset to load.

        Returns:
            pygame.Surface: The asset.
        """
        # Check if asset is already loaded
        if asset.__hash__() in self.transformed_asset:
            return self.transformed_asset[asset.__hash__()]

        # Load asset
        ## Get asset if it is already loaded, otherwise load it
        if asset.asset_name is not None and asset.asset_name in self.raw_asset:
            asset_surface = self.raw_asset[asset.asset_name]
        else:
            # Load asset based on asset name or asset surface
            if asset.asset_name is not None:
                asset_surface = pygame.image.load(
                    os.path.join("assets/frames", asset.asset_name + ".png")
                ).convert_alpha()
                self.raw_asset[asset.asset_name] = asset_surface
            elif asset.asset_surface is not None:
                asset_surface = asset.asset_surface
            else:
                raise ValueError(
                    "Either asset_name or asset_surface must be set when creating an asset."
                )

        # Apply transformations
        ## Apply rotation
        asset_surface = (
            pygame.transform.rotate(asset_surface, asset.rotation_factor)
            if asset.rotation_factor != 0
            else asset_surface
        )
        ## Apply scale
        asset_surface = (
            pygame.transform.scale(
                asset_surface,
                (
                    int(asset_surface.get_width() * asset.scale_factor),
                    int(asset_surface.get_height() * asset.scale_factor),
                ),
            )
            if asset.scale_factor != 1
            else asset_surface
        )
        ## Apply reverse
        asset_surface = (
            pygame.transform.flip(asset_surface, asset.reverse_factor, False)
            if asset.reverse_factor
            else asset_surface
        )
        ## Apply transparency
        if asset.transparency_factor != 0:
            if asset.transparency_factor != 0:
                alpha = int((1 - asset.transparency_factor) * 255)
                asset_surface.set_alpha(alpha)

        # Save asset (only if it is based on an image)
        if asset.asset_name is not None:
            self.transformed_asset[asset.__hash__()] = asset_surface

        # Check if memory is full
        if len(self.transformed_asset) > self.config.max_hashed_assets:
            # Delete a random asset
            del self.transformed_asset[
                np.random.choice(list(self.transformed_asset.keys()))
            ]

        # Return asset
        return asset_surface

    def get_asset_size(self, asset) -> tuple:
        """Get the size of an asset.

        Args:
            asset: The asset to load.

        Returns:
            tuple: The size of the asset.
        """
        # Get asset if it is already loaded, otherwise load it
        if asset.asset_name is not None and asset.asset_name in self.raw_asset:
            raw_asset_surface = self.raw_asset[asset.asset_name]
        elif asset.asset_name is not None:
            raw_asset_surface = pygame.image.load(
                os.path.join("assets/frames", asset.asset_name + ".png")
            ).convert_alpha()
            self.raw_asset[asset.asset_name] = raw_asset_surface
        elif asset.asset_surface is not None:
            raw_asset_surface = asset.asset_surface

        raw_asset_size = raw_asset_surface.get_size()

        return (
            int(raw_asset_size[0] * asset.scale_factor),
            int(raw_asset_size[1] * asset.scale_factor),
        )


asset_manager = AssetManager()


class Asset:
    asset_manager = asset_manager

    def __init__(self, asset_name: str = None, asset_surface: pygame.Surface = None):
        """A class to manage an asset. It is optimised to load images and apply common transformations very quickly.

        Args:
            asset_name (str): The name of the asseet to load. Defaults to None. MUST BE SET IF ASSET NAME IS NOT SET.
            asset_surface (pygame.Surface): The surface of the asset to load. Defaults to None. MUST BE SET IF ASSET NAME IS NOT SET.
        """
        # Set attributes
        self.asset_name = asset_name
        self.asset_surface = asset_surface

        # Check if arguments are valid
        if self.asset_name is None and self.asset_surface is None:
            raise ValueError(
                "Either asset_name or asset_surface must be set when creating an asset."
            )
        elif self.asset_name is not None and self.asset_surface is not None:
            raise ValueError(
                "Only one of asset_name or asset_surface must be set when creating an asset."
            )

        # Asset Transformations
        self.rotation_factor = 0
        """int: The angle to rotate the asset."""
        self.scale_factor = 1
        """float: The scale to apply to the asset."""
        self.reverse_factor = False
        """bool: Whether to reverse the asset."""
        self.transparency_factor = 0
        """float: The transparency of the asset. 0 is fully opaque, 1 is fully transparent."""

    def rotate(self, angle: int):
        """Rotate the asset.

        Args:
            angle (int): The angle to rotate the asset.

        Returns:
            Asset: The asset.
        """
        self.rotation_factor = angle
        return self

    def scale(self, scale: float):
        """Scale the asset.

        Args:
            scale (float): The scale to apply to the asset.

        Returns:
            Asset: The asset.
        """
        self.scale_factor = scale
        return self

    def reverse(self, reverse: bool):
        """Reverse the asset.

        Args:
            reverse (bool): Whether to reverse the asset.

        Returns:
            Asset: The asset.
        """
        self.reverse_factor = reverse
        return self

    def set_transparency(self, transparency: float):
        """Set the transparency of the asset.

        Args:
            transparency (float): The transparency of the asset. 0 is fully opaque, 1 is fully transparent.

        Returns:
            Asset: The asset.
        """
        # Check if transparency is valid
        if transparency < 0 or transparency > 1:
            raise ValueError("Transparency must be between 0 and 1.")
        self.transparency_factor = transparency
        return self

    def __hash__(self) -> str:
        """Hash the asset. This is used to store the asset in a dictionary.
        ONLY WORKS IF THE ASSET IS BASED ON AN IMAGE !

        Returns:
            str: The hash of the asset.
        """
        return f"{self.asset_name}_{self.rotation_factor}_{self.scale_factor}_{self.reverse_factor}_{self.transparency_factor}"

    def get_image(
        self, angle: int = 0, scale: int = 1, reverse: bool = 0, transparency: float = 0
    ) -> pygame.Surface:
        """Get the asset.

        Args:
            angle (int): The angle to rotate the asset. Defaults to 0.
            scale (int): The scale to apply to the asset. Defaults to 1.
            reverse (bool): Whether to reverse the asset. Defaults to False.
            transparency (float): The transparency of the asset. 0 is fully opaque, 1 is fully transparent. Defaults to 0.

        Returns:
            pygame.Surface: The asset.
        """
        # Save old transformations
        old_rotation_factor = self.rotation_factor
        old_scale_factor = self.scale_factor
        old_reverse_factor = self.reverse_factor
        old_transparency_factor = self.transparency_factor

        # Apply transformations
        self.rotation_factor += angle
        self.scale_factor *= scale
        self.reverse_factor = (
            not (self.reverse_factor) if reverse else self.reverse_factor
        )
        self.transparency_factor += transparency
        if self.transparency_factor < 0:
            self.transparency_factor = 0
        elif self.transparency_factor > 1:
            self.transparency_factor = 1

        # Get image
        image = self.asset_manager.get_image(self)

        # Revert transformations
        self.rotation_factor = old_rotation_factor
        self.scale_factor = old_scale_factor
        self.reverse_factor = old_reverse_factor
        self.transparency_factor = old_transparency_factor

        return image

    def get_size(self) -> tuple:
        """Get the size of the asset.

        Returns:
            tuple: The size of the asset.
        """
        return self.asset_manager.get_asset_size(self)
