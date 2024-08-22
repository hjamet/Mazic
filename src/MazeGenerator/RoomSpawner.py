import json
import os
from collections import namedtuple
from typing import List, Set, Tuple

from Entities.Maze.Decoration import Decoration
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Logger import Logger

AssetInfo = namedtuple("AssetInfo", ["id", "name", "rotation", "reverse"])
EntranceGroup = namedtuple("EntranceGroup", ["coordinates", "direction"])


class RoomSpawner:
    """Class for generating room entities from a JSON file."""

    # Constants for binary masks
    _ASSET_ID_MASK = 0x0FFFFFFF
    _FLIP_H_MASK = 0x80000000
    _FLIP_V_MASK = 0x40000000
    _ROTATION_MASK = 0x30000000

    _asset_names = {
        110: "wall_mid",
        112: "wall_outer_mid_left",
        219: "floor_1",
        220: "floor_3",
        221: "floor_4",
        222: "floor_5",
        223: "floor_6",
        224: "floor_8",
        228: "floor_spikes_anim_f3",
        307: "wall_edge_right",
        311: "wall_edge_tshape_left",
        312: "wall_edge_tshape_right",
        325: "wall_left",
        326: "wall_outer_front_left",
        327: "wall_outer_mid_right",
        328: "wall_outer_top_left",
        329: "wall_outer_top_right",
        330: "wall_right",
        331: "wall_top_left",
        333: "wall_top_right",
        332: "wall_top_mid",
    }

    def __init__(self, room_nbr: int, x: int = 0, y: int = 0) -> None:
        """
        Initialise le RoomSpawner et génère les entités de la salle.

        Args:
            room_nbr (int): Le numéro de la salle à générer.
            x (int): La coordonnée x du coin supérieur gauche du plus petit rectangle contenant la salle. Par défaut 0.
            y (int): La coordonnée y du coin supérieur gauche du plus petit rectangle contenant la salle. Par défaut 0.
        """
        self.logger = Logger(self.__class__.__name__)
        self.room_nbr = room_nbr
        self.x = x
        self.y = y

        # Charger les données de la salle
        with open(os.path.join("assets", "rooms", f"{room_nbr}.json"), "r") as f:
            data = json.load(f)

        # Créer les entités
        self.entities = []
        for layer in data["layers"]:
            for i, asset_nbr in enumerate(layer["chunks"][0]["data"]):
                if asset_nbr == 0:
                    continue

                asset_info = self._decode_asset(asset_nbr)
                tile_args = {
                    "x": self.x + (i % layer["chunks"][0]["width"]) * 16,
                    "y": self.y + (i // layer["chunks"][0]["width"]) * 16,
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
                    raise ValueError(f"Nom de couche inconnu : {layer['name']}")

        self._calculate_bounding_box()
        self.logger.info(f"{self.get_entrances()}")

    def overlaps_with(self, other_room: "RoomSpawner") -> bool:
        """
        Vérifie si cette salle chevauche une autre salle.

        Args:
            other_room (RoomSpawner): L'autre salle à vérifier pour le chevauchement.

        Returns:
            bool: True si les salles se chevauchent, False sinon.
        """
        # Vérifier si les boîtes englobantes se chevauchent
        if (
            self.top_left_x > other_room.bottom_right_x
            or self.bottom_right_x < other_room.top_left_x
            or self.top_left_y > other_room.bottom_right_y
            or self.bottom_right_y < other_room.top_left_y
        ):
            return False

        # Si les boîtes englobantes se chevauchent, vérifier les tuiles individuelles
        self_tiles = set((entity.x, entity.y) for entity in self.entities)
        other_tiles = set((entity.x, entity.y) for entity in other_room.entities)

        return bool(self_tiles.intersection(other_tiles))

    def _decode_asset(self, asset_number: int) -> AssetInfo:
        """
        Decode an asset number into an AssetInfo containing optimized asset information.

        Args:
            asset_number (int): The encoded asset number.

        Returns:
            AssetInfo: A namedtuple containing the optimized asset information.
        """
        asset_number -= 1
        asset_id = asset_number & self._ASSET_ID_MASK
        flip_h = bool(asset_number & self._FLIP_H_MASK)
        flip_v = bool(asset_number & self._FLIP_V_MASK)
        rotation = ((asset_number & self._ROTATION_MASK) >> 28) * 90

        # Optimize flip and rotation combinations
        if flip_h and flip_v:
            flip_h = flip_v = False
            rotation = (rotation + 180) % 360
        elif flip_v:
            flip_v = False
            flip_h = not flip_h
            rotation = (rotation + 180) % 360

        reverse = flip_h  # Now only horizontal flip is used

        asset_name = self._asset_names.get(asset_id, "error")

        return AssetInfo(
            id=asset_id, name=asset_name, rotation=rotation, reverse=reverse
        )

    def get_entities(self):
        """Return the list of generated entities."""
        return self.entities

    def get_entrances(self) -> Tuple[EntranceGroup, ...]:
        """
        Identifie et regroupe les cases vides adjacentes aux entrées (floors adjacents à des cases vides).

        Returns:
            Tuple[EntranceGroup, ...]: Groupes uniques d'entrées avec leurs coordonnées et directions.
        """
        floor_tiles = {(e.x, e.y) for e in self.entities if isinstance(e, Floor)}
        wall_tiles = {(e.x, e.y) for e in self.entities if isinstance(e, Wall)}
        directions = [
            (0, -16, "up"),
            (0, 16, "down"),
            (-16, 0, "left"),
            (16, 0, "right"),
        ]

        def get_empty_adjacent(x: int, y: int) -> Tuple[int, int, str]:
            """Trouve la case vide adjacente à une entrée et sa direction."""
            for dx, dy, direction in directions:
                adj_tile = (x + dx, y + dy)
                if adj_tile not in floor_tiles and adj_tile not in wall_tiles:
                    return (*adj_tile, direction)
            return None

        def get_entrance_group(x: int, y: int) -> Tuple[Set[Tuple[int, int]], str]:
            """Trouve récursivement les cases vides adjacentes aux entrées connectées."""
            group = set()
            stack = [(x, y)]
            direction = None
            while stack:
                cx, cy = stack.pop()
                empty_adj = get_empty_adjacent(cx, cy)
                if empty_adj:
                    ex, ey, direction = empty_adj
                    if (ex, ey) not in group:
                        group.add((ex, ey))
                        stack.extend(
                            (cx + dx, cy + dy)
                            for dx, dy, _ in directions
                            if (cx + dx, cy + dy) in floor_tiles
                            and (cx + dx, cy + dy) not in wall_tiles
                        )
            return group, direction

        entrances = set()
        processed = set()
        for tile in floor_tiles:
            if tile not in wall_tiles:
                empty_adj = get_empty_adjacent(*tile)
                if empty_adj and tile not in processed:
                    group, direction = get_entrance_group(*tile)
                    if group:
                        entrances.add(EntranceGroup(tuple(sorted(group)), direction))
                        processed.update(
                            tile
                            for x, y in group
                            for dx, dy, _ in directions
                            if (x - dx, y - dy) in floor_tiles
                            and (x - dx, y - dy) not in wall_tiles
                        )

        return tuple(entrances)

    def _calculate_bounding_box(self) -> None:
        """
        Calcule la boîte englobante de la salle basée sur ses entités.

        Cette méthode met à jour les attributs top_left_x, top_left_y, bottom_right_x et bottom_right_y.
        """
        if not self.entities:
            self.top_left_x = self.top_left_y = self.bottom_right_x = (
                self.bottom_right_y
            ) = 0
            return

        for entity in self.entities:
            entity.x += self.x
            entity.y += self.y

        self.top_left_x = min(entity.x for entity in self.entities)
        self.top_left_y = min(entity.y for entity in self.entities)
        self.bottom_right_x = max(entity.x for entity in self.entities)
        self.bottom_right_y = max(entity.y for entity in self.entities)
