import json
import os
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall

# for x in range(-10, 10):
#     for y in range(-10, 10):
#         if y != 0:
#             floor = Floor(x=x * 16, y=y * 16)
#             self.entity_manager.add(floor)
#         else:
#             wall = Wall(x=x * 16, y=y * 16)
#             self.entity_manager.add(wall)


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
                else:
                    raise ValueError(f"Unknown layer name: {layer['name']}")

    def get_entities(self):
        return self.entities
