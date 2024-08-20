from collections import namedtuple
from typing import Dict
import json
import os
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Entities.Maze.Decoration import Decoration

AssetInfo = namedtuple("AssetInfo", ["id", "name", "rotation", "reverse"])


class RoomSpawner:
    """Class for generating room entities from a JSON file."""

    # Constants for binary masks
    _ASSET_ID_MASK = 0x0FFFFFFF
    _FLIP_H_MASK = 0x80000000
    _FLIP_V_MASK = 0x40000000
    _ROTATION_MASK = 0x30000000

    def __init__(self, room_nbr: int) -> None:
        """
        Initialize the RoomSpawner and generate room entities.

        Args:
            room_nbr (int): The number of the room to generate.
        """
        # Dictionary of asset names (to be completed)
        self._asset_names = {
            219: "floor_1",
            220: "floor_3",
            221: "floor_4",
            222: "floor_5",
            223: "floor_6",
            224: "floor_8",
        }

        # Load room data
        with open(os.path.join("assets", "rooms", f"{room_nbr}.json"), "r") as f:
            data = json.load(f)

        # Create entities
        self.entities = []
        for layer in data["layers"]:
            for i, asset_nbr in enumerate(layer["chunks"][0]["data"]):
                if asset_nbr == 0:
                    continue

                asset_info = self._decode_asset(asset_nbr)
                tile_args = {
                    "x": (i % layer["chunks"][0]["width"]) * 16,
                    "y": (i // layer["chunks"][0]["width"]) * 16,
                    "assets_needed": {"idle": [asset_info.name]},
                    "rotation": asset_info.rotation,
                    "reverse": asset_info.reverse,
                }

                if layer["name"] == "floor":
                    self.entities.append(Floor(**tile_args))
                elif layer["name"] == "wall":
                    self.entities.append(Wall(**tile_args))
                elif layer["name"] == "decoration":
                    self.entities.append(Decoration(**tile_args))
                else:
                    raise ValueError(f"Unknown layer name: {layer['name']}")

    def _decode_asset(self, asset_number: int) -> AssetInfo:
        """
        Decode an asset number into an AssetInfo containing the asset information.

        Args:
            asset_number (int): The encoded asset number.

        Returns:
            AssetInfo: A namedtuple containing the asset information.
        """
        asset_id = asset_number & self._ASSET_ID_MASK
        flip_h = bool(asset_number & self._FLIP_H_MASK)
        flip_v = bool(asset_number & self._FLIP_V_MASK)
        rotation = ((asset_number & self._ROTATION_MASK) >> 28) * 90

        # Combine flip_h and flip_v into a single 'reverse' value
        reverse = flip_h or flip_v

        asset_name = self._asset_names.get(asset_id, f"error")

        return AssetInfo(
            id=asset_id, name=asset_name, rotation=rotation, reverse=reverse
        )

    def get_entities(self):
        """Return the list of generated entities."""
        return self.entities
