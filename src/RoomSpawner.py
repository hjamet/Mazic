import json
import os
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Entities.Maze.Decoration import Decoration


class RoomSpawner:

    def __init__(self, room_nbr: int) -> None:
        # Load room data
        with open(os.path.join("assets", "rooms", f"{room_nbr}.json"), "r") as f:
            data = json.load(f)

        # Create entities
        self.entities = []
        for layer in data["layers"]:
            for i, asset_nbr in enumerate(layer["chunks"][0]["data"]):

                # Check if the tile is not empty
                if asset_nbr == 0:
                    continue

                # Define the entity arguments
                tile_args = {
                    "x": (i % layer["chunks"][0]["width"]) * 16,
                    "y": (i // layer["chunks"][0]["width"]) * 16,
                }

                # Create the entity
                if layer["name"] == "floor":
                    self.entities.append(Floor(**tile_args))
                elif layer["name"] == "wall":
                    self.entities.append(Wall(**tile_args))
                elif layer["name"] == "decoration":
                    self.entities.append(Decoration(**tile_args))
                else:
                    raise ValueError(f"Unknown layer name: {layer['name']}")

    def get_entities(self):
        return self.entities
