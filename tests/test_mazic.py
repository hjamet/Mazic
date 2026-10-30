import os
import sys

# Ensure src/ is in sys.path and working directory is repo root for relative assets
os.environ["SDL_VIDEODRIVER"] = "dummy"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

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
from MazeGenerator.FogOfWar import FogOfWar
from EntityPlugins.SpellBook import SpellBook
from Entities.Monster import Monster, transform_into_immortal_monster
from UI.HUD import HUD
from Audio.SoundManager import SoundManager
from Mazic import Mazic


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


def test_fog_of_war_raycasting_and_wall_occlusion():
    """Vérifie que FogOfWar bloque la ligne de vue derrière un mur via raycasting Bresenham."""
    fow = FogOfWar(tile_size=16, vision_radius_tiles=6)
    walls = {(2, 0)}  # Un mur en x=2, y=0

    # Raycasting depuis le joueur en (0, 0)
    visible = fow.compute_fov(0, 0, walls, arcane_sight_active=False)

    assert (0, 0) in visible, "Player center tile must be visible"
    assert (1, 0) in visible, "Tile in front of wall must be visible"
    assert (2, 0) in visible, "Wall tile facing the player must be visible"
    assert (3, 0) not in visible, "Tile directly behind wall must be occluded"
    assert (4, 0) not in visible, "Tile further behind wall must be occluded"


def test_fog_of_war_memory_explored_tiles():
    """Vérifie que les tuiles explorées restent en mémoire (statut EXPLORED) quand le joueur s'éloigne."""
    fow = FogOfWar(tile_size=16, vision_radius_tiles=4)

    # Joueur en (0, 0)
    fow.update(0, 0, walls=set())
    assert fow.get_tile_visibility(0, 0) == "VISIBLE"
    assert (0, 0) in fow.visible_tiles
    assert (0, 0) in fow.explored_tiles

    # Joueur se déplace loin en (400, 400)
    fow.update(400, 400, walls=set())
    assert (0, 0) not in fow.visible_tiles, "Old tile must no longer be currently visible"
    assert fow.get_tile_visibility(0, 0) == "EXPLORED", "Explored tile must remain EXPLORED in memory"
    assert fow.get_tile_visibility(999, 999) == "UNEXPLORED", "Unvisited tile must be UNEXPLORED"


def test_spellbook_mana_consumption_and_regen():
    """Vérifie la consommation de mana par les sorts, le rejet si mana insuffisant et la régénération."""
    sb = SpellBook(max_mana=100.0, mana_regen_rate=10.0)
    assert sb.mana == 100.0

    # Sort Fireball (coût 10)
    res = sb.cast_fireball((0, 0), (100, 100))
    assert res is not None
    assert res["spell"] == "fireball"
    assert sb.mana == 90.0

    # Forcer mana bas pour tester le rejet
    sb.mana = 5.0
    res_fail = sb.cast_fireball((0, 0), (100, 100))
    assert res_fail is None, "Cast must fail when mana < cost"
    assert sb.mana == 5.0, "Mana must not be deducted on failed cast"

    # Régénération sur 2 secondes (10 mana/s -> +20)
    sb.update(2.0)
    assert sb.mana == 25.0

    # Régénération plafonnée au max_mana
    sb.update(50.0)
    assert sb.mana == 100.0


def test_spellbook_wall_alter_mechanic():
    """Vérifie que Brise-Mur détruit un mur (-> sol) ou crée un mur sur du sol libre."""
    sb = SpellBook()
    walls = {(5, 5), (6, 5)}
    floors = {(5, 6), (6, 6)}

    # 1. Détruire un mur
    res_destroy = sb.cast_wall_alter(5, 5, walls, floors)
    assert res_destroy == "DESTROYED_WALL"
    assert (5, 5) not in walls, "Wall must be removed from walls_set"
    assert (5, 5) in floors, "Tile must be added to floors_set"
    assert sb.mana == 75.0  # 100 - 25

    # 2. Créer un mur sur un sol libre
    res_create = sb.cast_wall_alter(5, 6, walls, floors)
    assert res_create == "CREATED_WALL"
    assert (5, 6) in walls, "Tile must be added to walls_set"
    assert (5, 6) not in floors, "Tile must be removed from floors_set"
    assert sb.mana == 50.0  # 75 - 25

    # 3. Cibler une coordonnée invalide (ni mur ni sol)
    res_invalid = sb.cast_wall_alter(100, 100, walls, floors)
    assert res_invalid is None
    assert sb.mana == 50.0, "Mana must not be consumed on invalid target"


def test_spellbook_arcane_sight_penetration():
    """Vérifie que le sort Arcane Sight traverse l'occultation des murs."""
    sb = SpellBook()
    fow = FogOfWar(tile_size=16, vision_radius_tiles=6)
    walls = {(2, 0)}

    # Sans Arcane Sight : la tuile (3, 0) derrière le mur est occultée
    fow.update(0, 0, walls, arcane_sight_active=False)
    assert (3, 0) not in fow.visible_tiles

    # Activation Arcane Sight (coût 20)
    ok = sb.cast_arcane_sight(duration=6.0)
    assert ok is True
    assert sb.is_arcane_sight_active is True
    assert sb.mana == 80.0

    # Avec Arcane Sight actif : la vision traverse les murs
    fow.update(0, 0, walls, arcane_sight_active=sb.is_arcane_sight_active)
    assert (3, 0) in fow.visible_tiles, "Arcane sight must penetrate walls"
    assert fow.get_tile_visibility(3, 0) == "VISIBLE"


def test_spellbook_blink_teleportation():
    """Vérifie que Blink téléporte sur du sol à portée, rejette les murs et les portées excessives."""
    sb = SpellBook()
    walls = {(2, 0)}
    floors = {(0, 0), (1, 0), (1, 1), (2, 1), (3, 1)}

    # Téléportation valide vers (16, 16) soit tuile (1, 1)
    new_pos = sb.cast_blink((0, 0), (16, 16), walls, floors, max_range_tiles=6)
    assert new_pos == (16.0, 16.0)
    assert sb.mana == 70.0  # 100 - 30

    # Téléportation invalide sur un mur (32, 0) soit tuile (2, 0)
    fail_wall = sb.cast_blink((16, 16), (32, 0), walls, floors, max_range_tiles=6)
    assert fail_wall is None, "Blink onto a wall must be rejected"
    assert sb.mana == 70.0

    # Téléportation invalide hors portée (distance > 6 * 16 = 96 px)
    fail_range = sb.cast_blink((16, 16), (500, 500), walls, floors, max_range_tiles=6)
    assert fail_range is None, "Blink beyond max range must be rejected"
    assert sb.mana == 70.0


def test_immortal_monster_transformation_on_death():
    """Vérifie la mécanique signature : à 0 PV le Mage devient un Monstre Immortel avec buff de vitesse."""
    char = Character(name="HeroMage", x=0, y=0)
    assert char.is_immortal_monster is False
    initial_speed = char.speed

    # Infliger des dégâts mortels
    char.damage(150)

    # Doit être transformé en Monstre Immortel
    assert char.is_immortal_monster is True, "Character must be marked as immortal monster"
    assert char.hp > 0, "HP must be restored upon immortal transformation"
    assert char.speed >= initial_speed * 1.3, "Speed must receive a 1.35x multiplier"
    assert char._is_dead is False, "Death state must be cleared"


def test_hud_minimap_generation_and_sound_manager_headless():
    """Vérifie la génération de la surface minimap et l'exécution sans erreur de SoundManager en headless."""
    hud = HUD()
    fow = FogOfWar()
    fow.explored_tiles = {(0, 0), (1, 0), (0, 1)}
    fow.visible_tiles = {(0, 0)}

    minimap_surf = hud.generate_minimap_surface(fow, None, (0, 0), (120, 120))
    assert isinstance(minimap_surf, pygame.Surface)
    assert minimap_surf.get_size() == (120, 120)

    # SoundManager headless
    sm = SoundManager()
    assert sm.play_fireball() is True
    assert sm.play_wall_alter() is True
    assert sm.play_arcane_sight() is True
    assert sm.play_blink() is True
    assert sm.play_transformation() is True


def test_mazic_pygame_wall_alter_mutates_entities():
    """Vérifie que apply_wall_alter altère réellement les entités Wall et Floor dans room et entity_manager."""
    game = Mazic()
    start_room = game.maze_manager.rooms[0]

    # Trouver un mur initial dans la salle
    initial_walls = [e for e in start_room.entities if isinstance(e, Wall)]
    assert len(initial_walls) > 0, "Initial room must contain walls"
    target_wall = initial_walls[0]
    gx, gy = int(target_wall.x // 16), int(target_wall.y // 16)

    # 1. Détruire le mur -> création d'un Floor
    res = game.apply_wall_alter(gx, gy)
    assert res in ("DESTROYED_WALL", "destroyed")
    assert target_wall not in start_room.entities, "Wall entity must be removed from room.entities"
    assert target_wall not in game.entity_manager.entities, "Wall entity must be removed from entity_manager"

    floors_at_tile = [
        e for e in start_room.entities if isinstance(e, Floor) and int(e.x // 16) == gx and int(e.y // 16) == gy
    ]
    assert len(floors_at_tile) == 1, "A new Floor entity must be created at the destroyed wall position"
    assert floors_at_tile[0] in game.entity_manager.entities, "New Floor must be present in entity_manager"

    # 2. Re-créer un mur sur ce sol -> suppression du Floor et création d'un Wall
    res2 = game.apply_wall_alter(gx, gy)
    assert res2 in ("CREATED_WALL", "created")
    assert floors_at_tile[0] not in start_room.entities, "Floor entity must be removed from room.entities"
    assert floors_at_tile[0] not in game.entity_manager.entities, "Floor must be removed from entity_manager"

    walls_at_tile = [
        e for e in start_room.entities if isinstance(e, Wall) and int(e.x // 16) == gx and int(e.y // 16) == gy
    ]
    assert len(walls_at_tile) == 1, "A new Wall entity must be created at the position"
    assert walls_at_tile[0] in game.entity_manager.entities, "New Wall must be present in entity_manager"


def test_mazic_pygame_fireball_and_immortal_monster_combat_loop():
    """Vérifie la boucle de combat Pygame : fireball contre monstre, collecte de cristaux, transformation et chasse des rivaux."""
    game = Mazic()
    assert len(game.monsters) >= 1, "Mazic must spawn at least one Guardian Demon"
    assert len(game.rival_mages) >= 1, "Mazic must spawn a rival mage"
    demon = game.monsters[0]
    assert demon in game.entity_manager.entities, "Demon must be in entity_manager"

    # 1. Tirer une boule de feu sur le démon
    demon.x = game.main_character.x + 30
    demon.y = game.main_character.y
    demon.hp = 20  # Fireball deals 25 damage, so this will kill it

    casted = game.cast_player_fireball((demon.x, demon.y))
    assert casted is True, "Player must successfully cast fireball"
    assert len(game.active_fireballs) == 1

    # Avancer le gameplay pour collision de la boule de feu
    game.step_gameplay(0.1, set())
    assert demon not in game.monsters, "Dead monster must be removed from game.monsters"
    assert demon not in game.entity_manager.entities, "Dead monster must be removed from entity_manager"
    assert game.main_character.spellbook.inventory["crystals"] >= 1, "Killing monster must grant a crystal"

    # 2. Attaque d'un monstre réduisant les PV du joueur à 0 -> Transformation en Monstre Immortel
    attacker = Monster(
        name="Lethal Demon",
        x=game.main_character.x + 5,
        y=game.main_character.y,
        damage_amount=150,
    )
    game.monsters.append(attacker)
    game.entity_manager.add(attacker)

    game.step_gameplay(0.1, set())
    assert game.main_character.is_immortal_monster is True, "Player must become an Immortal Monster upon 0 HP"

    # 3. Chasse des mages rivaux par le Monstre Immortel
    rival = game.rival_mages[0]
    rival.x = game.main_character.x + 6
    rival.y = game.main_character.y

    game.step_gameplay(0.1, set())
    assert rival not in game.rival_mages, "Slain rival must be removed from game.rival_mages"
    assert rival not in game.entity_manager.entities, "Slain rival must be removed from entity_manager"
    assert getattr(game.main_character, "hunters_slain", 0) == 1, "hunters_slain count must be 1"


def test_mazic_camera_fog_of_war_filtering():
    """Vérifie que Camera.update filtre les entités selon le FogOfWar (UNEXPLORED masqué, EXPLORED assombri/masqué, VISIBLE normal)."""
    class MockScreen:
        def __init__(self):
            self.blit_calls = []

        def fill(self, color):
            pass

        def get_width(self):
            return 800

        def get_height(self):
            return 600

        def blit(self, source, dest):
            self.blit_calls.append((source, dest))

    mock_screen = MockScreen()

    class MockGame:
        def __init__(self, screen_obj):
            self.screen = screen_obj
            self.fog_of_war = FogOfWar(tile_size=16)
            self.main_character = None

    game = MockGame(mock_screen)
    em = EntityManager()
    cam = Camera(game, em)
    cam.zoom = 1
    cam.x = 80
    cam.y = 80

    # Définir le statut du Fog of War
    # (0, 0) -> VISIBLE
    # (10, 10) -> EXPLORED
    # (20, 20) -> UNEXPLORED
    game.fog_of_war.visible_tiles = {(0, 0)}
    game.fog_of_war.explored_tiles = {(0, 0), (10, 10)}

    wall_visible = Wall(x=0, y=0)
    wall_explored = Wall(x=160, y=160)
    monster_explored = Monster(name="HiddenDemon", x=160, y=160)
    wall_unexplored = Wall(x=320, y=320)

    em.add(wall_visible)
    em.add(wall_explored)
    em.add(monster_explored)
    em.add(wall_unexplored)

    cam.update()

    # Vérifications :
    # 1. wall_unexplored (gx=20, gy=20) ne doit PAS être dessiné
    # 2. monster_explored (gx=10, gy=10) ne doit PAS être dessiné (entité mobile dans EXPLORED)
    # 3. wall_visible (gx=0, gy=0) et wall_explored (gx=10, gy=10) doivent être dessinés (2 blits)
    assert len(mock_screen.blit_calls) == 2, f"Expected exactly 2 blit calls (visible wall and explored wall), got {len(mock_screen.blit_calls)}"

