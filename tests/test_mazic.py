import os
import sys

# Ensure src/ is in sys.path and pygame runs in headless dummy mode
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import pygame

pygame.init()
pygame.display.set_mode((800, 600))

from MazeGenerator.RoomSpawner import RoomSpawner, EntranceGroup
from MazeGenerator.MazeManager import MazeManager
from EntityManager import EntityManager
from Entities.Maze.Floor import Floor
from Entities.Maze.Wall import Wall
from Entities.Character import Character
from Camera import Camera


def test_room_spawner_no_coordinate_accumulation():
    """Vérifie que RoomSpawner ne cumule pas d'offsets à l'instanciation ni lors de set_position."""
    room0 = RoomSpawner(1, 0, 0)
    local_coords = [(getattr(e, "_local_x", e.x), getattr(e, "_local_y", e.y)) for e in room0.entities]

    room = RoomSpawner(1, 16, 32)
    # Vérifier que les entités sont bien à 16 + local_x, 32 + local_y (et non 2*16 ou 2*32)
    for e, (lx, ly) in zip(room.entities, local_coords):
        assert e.x == 16 + lx
        assert e.y == 32 + ly
        assert e._local_x == lx
        assert e._local_y == ly

    # Plusieurs appels successifs à set_position ne doivent pas cumuler d'offset
    room.set_position(48, 64)
    for e, (lx, ly) in zip(room.entities, local_coords):
        assert e.x == 48 + lx
        assert e.y == 64 + ly

    room.set_position(48, 64)
    for e, (lx, ly) in zip(room.entities, local_coords):
        assert e.x == 48 + lx
        assert e.y == 64 + ly

    room.set_position(0, 0)
    for e, (lx, ly) in zip(room.entities, local_coords):
        assert e.x == lx
        assert e.y == ly


def test_all_room_templates_valid_and_have_entrances():
    """Charge 1.json, 2.json, 3.json, 4.json et vérifie leurs directions d'entrées et largeur de 2 tuiles."""
    expected_directions = {
        1: {"up", "down", "left", "right"},
        2: {"left", "right"},
        3: {"up", "down", "right"},
        4: {"up", "left"},
    }

    for room_id, expected_dirs in expected_directions.items():
        room = RoomSpawner(room_id, 0, 0)
        entrances = room.get_entrances()
        assert len(entrances) == len(expected_dirs), f"Room {room_id} has unexpected number of entrances"

        found_dirs = set()
        for entrance_group in entrances:
            assert isinstance(entrance_group, EntranceGroup)
            assert entrance_group.direction in expected_dirs
            found_dirs.add(entrance_group.direction)
            # Chaque entrée doit faire exactement 2 tuiles de large
            assert len(entrance_group.coordinates) == 2, f"Room {room_id} entrance {entrance_group.direction} width != 2"
            # Les deux tuiles de l'entrée doivent être distantes de 16 px (adjacentes)
            c1, c2 = entrance_group.coordinates
            dist = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
            assert dist == 16, f"Room {room_id} entrance tiles not contiguous: {c1}, {c2}"

        assert found_dirs == expected_dirs


def test_dynamic_maze_generation_alignment():
    """Instancie MazeManager, génère les salles voisines et vérifie absence de chevauchement et contiguïté."""
    em = EntityManager()
    mm = MazeManager(em, start_room_nbr=1)
    start_room = mm.rooms[0]
    mm._create_neighboring_rooms(start_room)

    # Vérifier que des salles voisines ont été générées
    assert len(mm.rooms) > 1

    # Vérifier qu'aucune salle ne chevauche une autre
    for i in range(len(mm.rooms)):
        for j in range(i + 1, len(mm.rooms)):
            assert not mm.rooms[i].overlaps_with(mm.rooms[j]), (
                f"Room {i} (nbr={mm.rooms[i].room_nbr}) overlaps with Room {j} (nbr={mm.rooms[j].room_nbr})"
            )

    # Vérifier que les entrées connectées sont contiguës à 16 px ou coïncident
    all_floors = set()
    for r in mm.rooms:
        for e in r.entities:
            if isinstance(e, Floor):
                all_floors.add((e.x, e.y))

    # Vérifier que les salles connectées sont contiguës (distance entre floors d'entrées <= 32 px)
    r0_floors = {(e.x, e.y) for e in mm.rooms[0].entities if isinstance(e, Floor)}
    for r in mm.rooms[1:]:
        r_floors = {(e.x, e.y) for e in r.entities if isinstance(e, Floor)}
        min_dist = min(abs(x0 - x1) + abs(y0 - y1) for x0, y0 in r0_floors for x1, y1 in r_floors)
        assert min_dist <= 32, f"Room {r.room_nbr} is not adjacent to the start room (min_dist={min_dist}px)"


def test_dead_end_sealing_on_blocked_entrance():
    """Place une salle bloquant une sortie et vérifie que _create_neighboring_rooms scelle l'impasse."""
    em = EntityManager()
    mm = MazeManager(em, start_room_nbr=4)  # Template 4 a des sorties 'up' et 'left'
    r0 = mm.rooms[0]

    # Forcer find_matching_room à retourner None pour simuler l'impossibilité de placer une salle
    mm.find_matching_room = lambda entrance_group: None

    entrances_before = r0.get_entrances(no_neighbors=True)
    assert len(entrances_before) > 0

    mm._create_neighboring_rooms(r0)

    # Vérifier que pour chaque entrée qui était ouverte, des Wall ont été placés
    for entrance_group in entrances_before:
        for wx, wy in entrance_group.coordinates:
            # Vérifier présence d'un Wall à ces coordonnées
            walls_at_coord = [
                e for e in r0.entities if isinstance(e, Wall) and e.x == wx and e.y == wy
            ]
            assert len(walls_at_coord) > 0, f"No Wall found at dead-end coordinate ({wx}, {wy})"
            # Vérifier absence de Floor à ces coordonnées
            floors_at_coord = [
                e for e in r0.entities if isinstance(e, Floor) and e.x == wx and e.y == wy
            ]
            assert len(floors_at_coord) == 0, f"Floor still present at dead-end coordinate ({wx}, {wy})"


def test_issue21_floor_has_no_hitbox():
    """Vérifie qu'après Camera.update(), Floor.rect is None tandis que Wall et Character ont un Rect valide."""
    class DummyGame:
        def __init__(self, screen_surf):
            self.screen = screen_surf

    screen = pygame.display.get_surface()
    game = DummyGame(screen)
    em = EntityManager()
    cam = Camera(game, em)
    em.add(cam)

    floor = Floor(x=50, y=50)
    wall = Wall(x=50, y=50)
    char = Character(name="wizzard_m", x=50, y=50)

    em.add(floor)
    em.add(wall)
    em.add(char)

    cam.update()

    assert floor.rect is None, f"Floor should have rect is None, but got {floor.rect}"
    assert isinstance(wall.rect, pygame.Rect), f"Wall should have valid pygame.Rect, got {wall.rect}"
    assert isinstance(char.rect, pygame.Rect), f"Character should have valid pygame.Rect, got {char.rect}"
