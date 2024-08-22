import json
import os
from collections import namedtuple
from typing import List, Set, Tuple

from Entities.Maze.Decoration import Decoration
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Logger import Logger

AssetInfo = namedtuple("AssetInfo", ["id", "name", "rotation", "reverse"])


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
            x (int): La coordonnée x de l'entité en haut à gauche de la salle. Par défaut 0.
            y (int): La coordonnée y de l'entité en haut à gauche de la salle. Par défaut 0.
        """
        self.logger = Logger(self.__class__.__name__)
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
            self.max_x <= other_room.min_x
            or other_room.max_x <= self.min_x
            or self.max_y <= other_room.min_y
            or other_room.max_y <= self.min_y
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

    def get_entrances(self) -> Tuple[Tuple[Tuple[int, int], ...], ...]:
        """
        Identifie et regroupe les entrées (floors adjacents à des cases vides).

        Returns:
            Tuple[Tuple[Tuple[int, int], ...]]: Groupes d'entrées coordonnées.
        """
        all_tiles = {(e.x, e.y) for e in self.entities}
        floor_tiles = {(e.x, e.y) for e in self.entities if isinstance(e, Floor)}
        directions = [(0, -16), (0, 16), (-16, 0), (16, 0)]

        def is_entrance(x: int, y: int) -> bool:
            """Vérifie si une tuile est une entrée."""
            return any((x + dx, y + dy) not in all_tiles for dx, dy in directions)

        def get_entrance_group(x: int, y: int) -> Set[Tuple[int, int]]:
            """Trouve récursivement les tuiles d'entrée adjacentes."""
            group = set()
            stack = [(x, y)]
            while stack:
                cx, cy = stack.pop()
                if (
                    (cx, cy) not in group
                    and (cx, cy) in floor_tiles
                    and is_entrance(cx, cy)
                ):
                    group.add((cx, cy))
                    stack.extend((cx + dx, cy + dy) for dx, dy in directions)
            return group

        entrances = []
        processed = set()
        for tile in floor_tiles:
            if tile not in processed and is_entrance(*tile):
                group = get_entrance_group(*tile)
                if group:
                    entrances.append(tuple(sorted(group)))
                    processed.update(group)

        return tuple(entrances)

    def _calculate_bounding_box(self) -> None:
        """
        Calcule la boîte englobante de la salle basée sur ses entités.

        Cette méthode met à jour les attributs min_x, max_x, min_y et max_y de la salle.
        """
        if not self.entities:
            self.min_x = self.max_x = self.min_y = self.max_y = 0
            return

        self.min_x = min(entity.x for entity in self.entities)
        self.max_x = (
            max(entity.x for entity in self.entities) + 16
        )  # +16 pour la largeur de la tuile
        self.min_y = min(entity.y for entity in self.entities)
        self.max_y = (
            max(entity.y for entity in self.entities) + 16
        )  # +16 pour la hauteur de la tuile
