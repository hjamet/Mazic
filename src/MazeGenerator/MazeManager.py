import os
import random
from typing import List, Optional, Tuple, Set

from EntityManager import Entity

from .RoomSpawner import RoomSpawner


class MazeManager:
    """Manages the rooms of the maze and their positioning."""

    def __init__(self, start_room_nbr: int = None):
        """
        Initialize the maze manager with a starting room and its neighbors.

        Args:
            start_room_nbr (int, optional): Number of the starting room. If None, a random room is chosen.
        """
        # Choisir une salle de départ aléatoire si non spécifiée
        if start_room_nbr is None:
            room_files = [f for f in os.listdir("assets/rooms") if f.endswith(".json")]
            start_room_nbr = int(random.choice(room_files).split(".")[0])

        # Créer la première salle
        self.rooms: List[RoomSpawner] = [RoomSpawner(start_room_nbr, 0, 0)]
        self.room_positions: List[Tuple[int, int]] = [(0, 0)]

        # Obtenir les groupes d'entrées de la première salle
        start_room_entrances = self.rooms[0].get_entrances()

        # Ajouter des salles voisines pour chaque groupe d'entrées
        for entrance_group in start_room_entrances:

            # Trouver une salle compatible
            new_room = self.find_matching_room(entrance_group)
            if new_room:
                new_room_spawner, position = new_room
                self.add_room(new_room_spawner.room_nbr, position)

    def add_room(self, room_nbr: int, position: Tuple[int, int]) -> bool:
        """
        Add a new room to the maze.

        Args:
            room_nbr (int): Number of the new room.
            position (Tuple[int, int]): Relative position of the new room.

        Returns:
            bool: True if the room was successfully added, False otherwise.
        """
        x, y = position
        new_room = RoomSpawner(room_nbr, x * 8, y * 8)  # Multiply by 16 for tile size

        self.rooms.append(new_room)
        self.room_positions.append(position)
        return True

    def get_entity_room(self, entity: Entity) -> Optional[RoomSpawner]:
        """
        Identify the room in which an entity is located.

        Args:
            entity (Entity): The entity to locate.

        Returns:
            Optional[RoomSpawner]: The room containing the entity, or None if not found.
        """
        for room in self.rooms:
            if (
                room.min_x <= entity.x < room.max_x
                and room.min_y <= entity.y < room.max_y
            ):
                return room
        return None

    def find_matching_room(
        self, exits: List[Tuple[Tuple[int, int], ...]]
    ) -> Optional[Tuple[RoomSpawner, Tuple[int, int]]]:
        """
        Trouve une salle compatible avec les groupes de sorties donnés.

        Args:
            exits (List[Tuple[Tuple[int, int], ...]]): Liste des groupes de coordonnées des sorties.

        Returns:
            Optional[Tuple[RoomSpawner, Tuple[int, int]]]: Tuple contenant la salle compatible
            et sa position relative, ou None si aucune salle n'est trouvée.
        """
        # Obtenir la liste des fichiers de salle disponibles
        room_files = [f for f in os.listdir("assets/rooms") if f.endswith(".json")]

        # Mélanger la liste pour une sélection aléatoire
        random.shuffle(room_files)

        for room_file in room_files:
            room_nbr = int(room_file.split(".")[0])

            # Créer une salle temporaire
            temp_room = RoomSpawner(room_nbr)
            temp_entrances = temp_room.get_entrances()

            # Essayer chaque groupe d'entrées de la nouvelle salle
            for entrance_group in temp_entrances:
                # Vérifier si les tailles des groupes correspondent
                if len(exits) == len(entrance_group):
                    # Calculer la position relative basée sur la première entrée/sortie
                    exit_x, exit_y = exits[0]
                    entrance_x, entrance_y = entrance_group[0]
                    rel_x = (exit_x - entrance_x) // 16
                    rel_y = (exit_y - entrance_y) // 16

                    # Vérifier si la salle peut être placée à cette position
                    if self.can_place_room(temp_room, (rel_x, rel_y)):
                        # Vérifier si toutes les entrées correspondent aux sorties
                        if all(
                            (exit_x - entrance_x) // 16 == rel_x
                            and (exit_y - entrance_y) // 16 == rel_y
                            for (exit_x, exit_y), (entrance_x, entrance_y) in zip(
                                exits, entrance_group
                            )
                        ):
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
