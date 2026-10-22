import os
import random
from collections import namedtuple
from typing import List, NamedTuple, Optional, Set, Tuple

import numpy as np

from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from EntityManager import Entity
from Logger import Logger

from .RoomSpawner import RoomSpawner, EntranceGroup


class LoadUnloadResult(NamedTuple):
    to_load: List[Entity]
    to_unload: List[Entity]


class MazeManager:
    def __init__(self, entity_manager, start_room_nbr: Optional[int] = None) -> None:
        """
        Initialize the maze manager with a starting room and its neighbors.

        Args:
            entity_manager (EntityManager): The entity manager instance.
            start_room_nbr (int, optional): Number of the starting room. If None, a random room is chosen.
        """
        self.logger = Logger(self.__class__.__name__)
        self.entity_manager = entity_manager

        # Initialiser la grille
        self.grid = np.array([[0]], dtype=int)
        self.grid_origin = (0, 0)

        # Choisir une salle de départ aléatoire si non spécifiée
        if start_room_nbr is None:
            room_files = [f for f in os.listdir("assets/rooms") if f.endswith(".json")]
            start_room_nbr = int(random.choice(room_files).split(".")[0])

        # Créer la première salle
        self.rooms: List[RoomSpawner] = [RoomSpawner(start_room_nbr, 0, 0)]
        self.room_positions: List[Tuple[int, int]] = [(0, 0)]

        # Mettre à jour la grille
        self._write_room_to_grid(0)

        self.loaded_rooms = []

    def _write_room_to_grid(self, room_index: int) -> None:
        """
        Write the room to the grid.

        Args:
            room_index (int): Index of the room in the list of rooms.
        """
        room = self.rooms[room_index]

        # Check if the room is out of bounds
        min_x = (room.top_left_x // 16) - self.grid_origin[0]
        min_y = (room.top_left_y // 16) - self.grid_origin[1]
        max_x = (room.bottom_right_x // 16) - self.grid_origin[0]
        max_y = (room.bottom_right_y // 16) - self.grid_origin[1]
        grid_height, grid_width = self.grid.shape

        # Create a bigger grid if the room is out of bounds
        if min_x < 0 or min_y < 0 or max_x >= grid_width or max_y >= grid_height:
            new_min_x = min(0, min_x)
            new_min_y = min(0, min_y)
            new_max_x = max(grid_width - 1, max_x)
            new_max_y = max(grid_height - 1, max_y)

            new_grid = np.full(
                (new_max_y - new_min_y + 1, new_max_x - new_min_x + 1), 0, dtype=int
            )
            new_grid[
                -new_min_y : grid_height - new_min_y,
                -new_min_x : grid_width - new_min_x,
            ] = self.grid

            self.grid = new_grid

            # Update grid_origin
            self.grid_origin = (
                self.grid_origin[0] + new_min_x,
                self.grid_origin[1] + new_min_y,
            )

        # Write room entities to grid
        for entity in room.entities:
            if isinstance(entity, Floor):
                entity_x = (entity.x // 16) - self.grid_origin[0]
                entity_y = (entity.y // 16) - self.grid_origin[1]
                self.grid[entity_y, entity_x] = room_index + 1

    def add_room(self, room_nbr: int, position: Tuple[int, int]) -> bool:
        """
        Add a new room to the maze and update the grid.

        Args:
            room_nbr (int): Number of the new room.
            position (Tuple[int, int]): Relative position of the new room.

        Returns:
            bool: True if the room was successfully added, False otherwise.
        """
        x, y = position
        new_room = RoomSpawner(room_nbr, x * 16, y * 16)

        # Ajouter la nouvelle salle
        room_index = len(self.rooms)
        self.rooms.append(new_room)
        self.room_positions.append(position)

        # Mettre à jour la grille avec la nouvelle salle
        self._write_room_to_grid(room_index)

        # Save grid to file
        os.makedirs("logs", exist_ok=True)
        np.savetxt("logs/grid.csv", self.grid, delimiter=" ", fmt="%d")

        return True

    def find_matching_room(
        self, entrance_group
    ) -> Optional[Tuple[RoomSpawner, Tuple[int, int]]]:
        """
        Trouve une salle compatible avec le groupe d'entrées donné.

        Args:
            entrance_group (EntranceGroup): Groupe d'entrées avec coordonnées et direction.

        Returns:
            Optional[Tuple[RoomSpawner, Tuple[int, int]]]: Tuple contenant la salle compatible
            et sa position relative, ou None si aucune salle n'est trouvée.
        """
        room_files = [f for f in os.listdir("assets/rooms") if f.endswith(".json")]
        random.shuffle(room_files)

        for room_file in room_files:
            room_nbr = int(room_file.split(".")[0])
            temp_room = RoomSpawner(room_nbr)
            temp_entrances = temp_room.get_entrances()

            for temp_entrance_group in temp_entrances:
                if len(entrance_group.coordinates) == len(
                    temp_entrance_group.coordinates
                ) and self.__exit_entrance_direction_match(
                    entrance_group.direction, temp_entrance_group.direction
                ):
                    exit_x, exit_y = entrance_group.coordinates[0]
                    entrance_x, entrance_y = temp_entrance_group.coordinates[0]
                    rel_x = (exit_x - entrance_x) // 16
                    rel_y = (exit_y - entrance_y) // 16

                    if self.can_place_room(temp_room, (rel_x, rel_y)):
                        if all(
                            (ex - enx) // 16 == rel_x and (ey - eny) // 16 == rel_y
                            for (ex, ey), (enx, eny) in zip(
                                entrance_group.coordinates,
                                temp_entrance_group.coordinates,
                            )
                        ):
                            return temp_room, (rel_x, rel_y)

        return None

    def __exit_entrance_direction_match(
        self, entrance_direction: str, exit_direction: str
    ) -> bool:
        """
        Vérifie si la direction de l'entrée correspond à la direction de la sortie.

        Args:
            entrance_direction (str): Direction de l'entrée.
            exit_direction (str): Direction de la sortie.

        Returns:
            bool: True si les directions correspondent, False sinon.
        """
        if entrance_direction == "up":
            return exit_direction == "down"
        elif entrance_direction == "down":
            return exit_direction == "up"
        elif entrance_direction == "left":
            return exit_direction == "right"
        elif entrance_direction == "right":
            return exit_direction == "left"
        return False

    def can_place_room(self, room: RoomSpawner, position: Tuple[int, int]) -> bool:
        """
        Vérifie si une salle peut être placée à une position donnée.

        Args:
            room (RoomSpawner): La salle à placer.
            position (Tuple[int, int]): La position relative où placer la salle.

        Returns:
            bool: True si la salle peut être placée, False sinon.
        """
        x, y = position
        room.set_position(x * 16, y * 16)

        for existing_room in self.rooms:
            if room.overlaps_with(existing_room):
                return False

        return True

    def _is_entrance_already_connected(
        self, entrance_group: EntranceGroup
    ) -> bool:
        """
        Vérifie si une entrée est déjà connectée à une autre salle.
        """
        direction_offsets = {
            "up": (0, -16),
            "down": (0, 16),
            "left": (-16, 0),
            "right": (16, 0),
        }
        dx, dy = direction_offsets.get(entrance_group.direction, (0, 0))
        target_positions = set()
        for ex, ey in entrance_group.coordinates:
            target_positions.add((ex, ey))
            target_positions.add((ex + dx, ey + dy))

        for room in self.rooms:
            for entity in room.entities:
                if isinstance(entity, Floor) and (entity.x, entity.y) in target_positions:
                    return True
        return False

    def _seal_entrance_as_dead_end(
        self, room: RoomSpawner, entrance_group: EntranceGroup
    ) -> List[Wall]:
        """
        Ferme une entrée en impasse en y plaçant des murs.

        Args:
            room (RoomSpawner): La salle dont l'entrée doit être scellée.
            entrance_group (EntranceGroup): Le groupe d'entrées à sceller.

        Returns:
            List[Wall]: La liste des murs créés.
        """
        created_walls = []
        for wx, wy in entrance_group.coordinates:
            wall = Wall(x=wx, y=wy, assets_needed={"idle": ["wall_mid"]})
            wall._local_x = wx - room.x
            wall._local_y = wy - room.y

            floors_to_remove = [
                e for e in room.entities if isinstance(e, Floor) and e.x == wx and e.y == wy
            ]
            for floor_entity in floors_to_remove:
                room.entities.remove(floor_entity)
                if self.entity_manager is not None and hasattr(self.entity_manager, "remove"):
                    if floor_entity in getattr(self.entity_manager, "entities", []):
                        self.entity_manager.remove(floor_entity)

            room.entities.append(wall)
            if self.entity_manager is not None and hasattr(self.entity_manager, "add"):
                self.entity_manager.add(wall)

            # Mettre à jour self.grid
            grid_x = (wx // 16) - self.grid_origin[0]
            grid_y = (wy // 16) - self.grid_origin[1]
            if 0 <= grid_y < self.grid.shape[0] and 0 <= grid_x < self.grid.shape[1]:
                self.grid[grid_y, grid_x] = 0

            created_walls.append(wall)

        room._calculate_bounding_box()
        return created_walls

    def get_all_entities(self) -> List[Entity]:
        """
        Returns a list of all entities currently loaded in all rooms.

        Returns:
            List[Entity]: List of unique entities present in the maze.
        """
        all_entities = []
        for room in self.rooms:
            all_entities.extend(room.entities)
        return list(set(all_entities))

    def load_unload_rooms(self, entity: Entity) -> LoadUnloadResult:
        """
        Charge et décharge les salles en fonction de la position de l'entité.
        Crée également les salles voisines lors du chargement d'une nouvelle salle.

        Args:
            entity (Entity): L'entité dont la position est utilisée pour déterminer les salles à charger/décharger.

        Returns:
            LoadUnloadResult: Named tuple contenant les listes des entités chargées et déchargées.
        """
        # Calcul de la position de l'entité sur la grille
        entity_grid_x = (entity.x // 16) - self.grid_origin[0]
        entity_grid_y = (entity.y // 16) - self.grid_origin[1]

        # Détermination des salles voisines
        radius = 10
        min_x, max_x = max(0, entity_grid_x - radius), min(
            self.grid.shape[1], entity_grid_x + radius + 1
        )
        min_y, max_y = max(0, entity_grid_y - radius), min(
            self.grid.shape[0], entity_grid_y + radius + 1
        )
        neighboring_room_indices = set(
            self.grid[min_y:max_y, min_x:max_x].flatten()
        ) - {0}
        neighboring_room_indices = {index - 1 for index in neighboring_room_indices}

        newly_loaded_entities = []
        for room_index in neighboring_room_indices.copy():
            if (
                room_index >= 0
                and room_index < len(self.rooms)
                and room_index not in self.loaded_rooms
            ):
                room = self.rooms[room_index]
                newly_loaded_entities.extend(room.entities)
                self.loaded_rooms.append(room_index)
                self.logger.info(f"Chargement de la salle {room.room_nbr}.")

                # Création des salles voisines
                self._create_neighboring_rooms(room)

        # Déchargement des salles non nécessaires
        unloaded_entities = []
        rooms_to_unload = set(self.loaded_rooms) - neighboring_room_indices
        for room_index in rooms_to_unload:
            room = self.rooms[room_index]
            unloaded_entities.extend(room.entities)
            self.loaded_rooms.remove(room_index)
            self.logger.info(f"Déchargement de la salle {room.room_nbr}.")

        return LoadUnloadResult(newly_loaded_entities, unloaded_entities)

    def _create_neighboring_rooms(self, room: RoomSpawner) -> None:
        """
        Crée les salles voisines pour une salle donnée.

        Args:
            room (RoomSpawner): La salle pour laquelle créer les voisines.
        """
        if room.has_neighbours:
            return
        entrances = room.get_entrances(no_neighbors=True)
        # Find id of the room in the list
        room_index = self.rooms.index(room)
        print(f"Création des salles voisines pour la salle {room_index}.")
        for entrance_group in entrances:
            if self._is_entrance_already_connected(entrance_group):
                continue
            new_room = self.find_matching_room(entrance_group)
            if new_room:
                new_room_spawner, position = new_room
                if self.add_room(new_room_spawner.room_nbr, position):
                    self.logger.info(f"Nouvelle salle créée: {len(self.rooms) - 1}.")
            else:
                self._seal_entrance_as_dead_end(room, entrance_group)
        room.has_neighbours = True
