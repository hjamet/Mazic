import os
import random
from typing import List, Optional, Tuple, Set

from EntityManager import Entity
from Entities.Maze.Floor import Floor

from .RoomSpawner import RoomSpawner
from typing import List, Tuple, Optional
import numpy as np

import numpy as np
from typing import List, Tuple, Optional


class MazeManager:
    def __init__(self, start_room_nbr: int = None):
        """
        Initialize the maze manager with a starting room and its neighbors.

        Args:
            start_room_nbr (int, optional): Number of the starting room. If None, a random room is chosen.
        """
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

        # Obtenir les groupes d'entrées de la première salle
        start_room_entrances = self.rooms[0].get_entrances()

        # Ajouter des salles voisines pour chaque groupe d'entrées
        for entrance_group in start_room_entrances:
            new_room = self.find_matching_room(entrance_group)
            if new_room:
                new_room_spawner, position = new_room
                self.add_room(new_room_spawner.room_nbr, position)

        # To csv
        np.savetxt("maze.csv", self.grid, delimiter=" ", fmt="%d")

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
        new_room = RoomSpawner(room_nbr, x * 8, y * 8)

        # Ajouter la nouvelle salle
        room_index = len(self.rooms)
        self.rooms.append(new_room)
        self.room_positions.append(position)

        # Mettre à jour la grille avec la nouvelle salle
        self._write_room_to_grid(room_index)

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
                            # Remove empty columns and rows between the rooms
                            if entrance_group.direction == "up":
                                rel_y += 2
                            elif entrance_group.direction == "down":
                                rel_y -= 2
                            elif entrance_group.direction == "left":
                                rel_x += 1
                            elif entrance_group.direction == "right":
                                rel_x -= 1
                            return temp_room, (rel_x, rel_y)

        return None

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
        room.x = x * 16
        room.y = y * 16
        room._calculate_bounding_box()

        for existing_room in self.rooms:
            if room.overlaps_with(existing_room):
                return False

        return True

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
