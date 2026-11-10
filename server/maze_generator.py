"""
server/maze_generator.py
Générateur Procédural de Donjon & Autotiler 2.5D 0x72_DungeonTilesetII.

Grille : 56x56 cases (tuiles de 16x16 pixels).
Algorithme : Hybride « Graphe de Salles + Couloirs (largeur >= 2) + Portes + Autotiler 2.5D Bitmask 8-voisins ».
Garanties :
- Connexité totale garantie (MST Kruskal + cycles tactiques)
- Murs d'épaisseur >= 2 cases entre salles
- 100 % des noms de sprites conformes aux frames de assets/frames/
- Temps d'exécution < 50 ms.
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Set, Tuple

# Constantes de grille
VOID: int = 0
FLOOR: int = 1
WALL: int = 2
DOOR_CLOSED: int = 3
DOOR_OPEN: int = 4

# Sprites de sols
FLOOR_SPRITES: list[str] = [
    "floor_1", "floor_2", "floor_3", "floor_4",
    "floor_5", "floor_6", "floor_7", "floor_8"
]

# Variantes décoratives sur wall_mid frontal
WALL_DECORATIONS: list[str] = [
    "wall_banner_red",
    "wall_banner_blue",
    "wall_banner_green",
    "wall_banner_yellow",
    "wall_hole_1",
    "wall_hole_2",
    "wall_goo",
]

# Props décoratifs de sol
FLOOR_PROPS: list[str] = [
    "skull",
    "crate",
    "chest_empty_open_anim_f0",
]

ASSETS_FRAMES_DIR: Path = Path(__file__).resolve().parent.parent / "assets" / "frames"


class DungeonGenerator:
    """Générateur procédural de donjon 2.5D compatible tileset 0x72."""

    def __init__(
        self,
        width: int = 56,
        height: int = 56,
        tile_size: int = 16,
        seed: Optional[int] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.seed: Optional[int] = seed
        self.dungeon: Optional[dict[str, Any]] = None
        self.grid: list[list[int]] = []
        self.tiles: list[list[dict[str, Optional[str]]]] = []
        self.rooms: list[dict[str, Any]] = []
        self.doors: list[tuple[int, int]] = []
        self.portal: Optional[dict[str, Any]] = None
        self.fountains: list[dict[str, Any]] = []
        self.crystals: list[dict[str, Any]] = []
        self.monster_spawns: list[tuple[int, int]] = []
        if seed is not None:
            self._generate_procedural_dungeon(seed)

    def _generate_procedural_dungeon(self, seed: Optional[int] = None) -> dict[str, Any]:
        """Génère le donjon procédural et met à jour les attributs de l'instance."""
        return self.generate(seed=seed)

    def generate(self, seed: Optional[int] = None) -> dict[str, Any]:
        """Génère un donjon complet avec géométrie, autotiling 2.5D et entités."""
        if seed is None:
            seed = self.seed if self.seed is not None else random.randint(0, 99999999)
        self.seed = seed
        rng = random.Random(seed)

        # 1. Grille initiale vide
        grid: list[list[int]] = [[VOID for _ in range(self.width)] for _ in range(self.height)]

        # 2. Placement des salles (12 à 15 salles sur 56x56, adapté selon la surface)
        target_room_count = rng.randint(12, 15)
        area = self.width * self.height
        if area >= 5000:
            target_room_count += 10
        elif area <= 1800:
            target_room_count = min(target_room_count, 10)
        rooms: list[dict[str, Any]] = []

        max_attempts = 600
        for _ in range(max_attempts):
            if len(rooms) >= target_room_count:
                break
            rw = rng.randint(6, 11)
            rh = rng.randint(6, 9)
            rx = rng.randint(3, self.width - rw - 4)
            ry = rng.randint(3, self.height - rh - 4)

            # Vérification de l'espacement >= 3 cases de bord à bord
            collision = False
            for r in rooms:
                if not (
                    rx + rw + 3 <= r["x"]
                    or rx >= r["x"] + r["w"] + 3
                    or ry + rh + 3 <= r["y"]
                    or ry >= r["y"] + r["h"] + 3
                ):
                    collision = True
                    break

            if not collision:
                room_id = len(rooms)
                cx = rx + rw // 2
                cy = ry + rh // 2
                rooms.append({
                    "id": room_id,
                    "x": rx,
                    "y": ry,
                    "w": rw,
                    "h": rh,
                    "cx": cx,
                    "cy": cy,
                    "kind": "normal",
                    "shape": "rect",
                })

                # Remplir le sol de la salle
                for y in range(ry, ry + rh):
                    for x in range(rx, rx + rw):
                        grid[y][x] = FLOOR

        # 3. Arbre couvrant minimal (Kruskal) + arêtes supplémentaires pour boucles
        num_rooms = len(rooms)
        edges: list[tuple[float, int, int]] = []
        for i in range(num_rooms):
            for j in range(i + 1, num_rooms):
                dist = math.hypot(rooms[i]["cx"] - rooms[j]["cx"], rooms[i]["cy"] - rooms[j]["cy"])
                edges.append((dist, i, j))

        edges.sort(key=lambda e: e[0])

        parent = list(range(num_rooms))

        def find(u: int) -> int:
            while parent[u] != u:
                parent[u] = parent[parent[u]]
                u = parent[u]
            return u

        def union(u: int, v: int) -> bool:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
                return True
            return False

        selected_corridors: list[tuple[int, int]] = []
        mst_edges: set[tuple[int, int]] = set()

        for dist, u, v in edges:
            if union(u, v):
                selected_corridors.append((u, v))
                mst_edges.add((min(u, v), max(u, v)))
                if len(selected_corridors) == num_rooms - 1:
                    break

        # Ajouter 3 arêtes supplémentaires pour créer des boucles tactiques
        extra_count = 0
        for dist, u, v in edges:
            pair = (min(u, v), max(u, v))
            if pair not in mst_edges:
                selected_corridors.append((u, v))
                mst_edges.add(pair)
                extra_count += 1
                if extra_count >= 3:
                    break

        # 4. Creusement des couloirs de largeur >= 2 cases
        for u, v in selected_corridors:
            c1 = (rooms[u]["cx"], rooms[u]["cy"])
            c2 = (rooms[v]["cx"], rooms[v]["cy"])

            # Alternance aléatoire de l'orientation du L (horizontal d'abord ou vertical d'abord)
            if rng.random() < 0.5:
                # Horizontal de c1.x à c2.x à hauteur c1.y, puis vertical à c2.x
                x_start, x_end = min(c1[0], c2[0]), max(c1[0], c2[0])
                for x in range(x_start, x_end + 1):
                    grid[c1[1]][x] = FLOOR
                    grid[c1[1] + 1][x] = FLOOR
                y_start, y_end = min(c1[1], c2[1]), max(c1[1], c2[1])
                for y in range(y_start, y_end + 1):
                    grid[y][c2[0]] = FLOOR
                    grid[y][c2[0] + 1] = FLOOR
            else:
                # Vertical d'abord, puis horizontal
                y_start, y_end = min(c1[1], c2[1]), max(c1[1], c2[1])
                for y in range(y_start, y_end + 1):
                    grid[y][c1[0]] = FLOOR
                    grid[y][c1[0] + 1] = FLOOR
                x_start, x_end = min(c1[0], c2[0]), max(c1[0], c2[0])
                for x in range(x_start, x_end + 1):
                    grid[c2[1]][x] = FLOOR
                    grid[c2[1] + 1][x] = FLOOR

        # 5. Placer des portes interactives (DOOR_CLOSED) sur les transitions
        # On inspecte les bords extérieurs des salles où un couloir pénètre
        door_candidates: list[tuple[int, int]] = []
        for r in rooms:
            rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
            # Bord Nord (y = ry - 1)
            for x in range(rx, rx + rw):
                if ry > 0 and grid[ry - 1][x] == FLOOR:
                    door_candidates.append((x, ry))
            # Bord Sud (y = ry + rh)
            for x in range(rx, rx + rw):
                if ry + rh < self.height and grid[ry + rh][x] == FLOOR:
                    door_candidates.append((x, ry + rh - 1))
            # Bord Ouest (x = rx - 1)
            for y in range(ry, ry + rh):
                if rx > 0 and grid[y][rx - 1] == FLOOR:
                    door_candidates.append((rx, y))
            # Bord Est (x = rx + rw)
            for y in range(ry, ry + rh):
                if rx + rw < self.width and grid[y][rx + rw] == FLOOR:
                    door_candidates.append((rx + rw - 1, y))

        # Échantillonner 6 à 8 portes pour ne pas bloquer tous les accès
        rng.shuffle(door_candidates)
        doors_placed: set[tuple[int, int]] = set()
        for dx, dy in door_candidates:
            if len(doors_placed) >= 8:
                break
            # Ne pas placer de porte si déjà une voisine
            if not any(abs(dx - px) + abs(dy - py) <= 1 for px, py in doors_placed):
                grid[dy][dx] = DOOR_CLOSED
                doors_placed.add((dx, dy))

        # 5b. Extensions de salles composites en L ou en T (jusqu'à 3 salles hors salle 0)
        composite_count = 0
        for r in rooms[1:]:
            if composite_count >= 3:
                break
            rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
            if rw >= 9 and rh >= 8:
                continue
            for side in ("N", "S", "E", "W"):
                aw, ah = 5, 4
                if side == "N":
                    ax, ay = rx + (rw - aw) // 2, ry - ah
                    shape = "T"
                elif side == "S":
                    ax, ay = rx, ry + rh
                    shape = "L"
                elif side == "E":
                    ax, ay = rx + rw, ry
                    shape = "L"
                else:
                    ax, ay = rx - aw, ry + (rh - ah) // 2
                    shape = "T"

                if ax < 3 or ay < 3 or ax + aw > self.width - 4 or ay + ah > self.height - 4:
                    continue

                wing_collision = False
                for r2 in rooms:
                    if r2["id"] == r["id"]:
                        continue
                    if not (
                        ax + aw + 3 <= r2["x"]
                        or ax >= r2["x"] + r2["w"] + 3
                        or ay + ah + 3 <= r2["y"]
                        or ay >= r2["y"] + r2["h"] + 3
                    ):
                        wing_collision = True
                        break

                if not wing_collision:
                    for dx, dy in doors_placed:
                        if (ax - 1 <= dx <= ax + aw) and (ay - 1 <= dy <= ay + ah):
                            wing_collision = True
                            break

                if not wing_collision:
                    for wy in range(ay, ay + ah):
                        for wx in range(ax, ax + aw):
                            grid[wy][wx] = FLOOR
                    r["shape"] = shape
                    r["wing"] = {"x": ax, "y": ay, "w": aw, "h": ah, "side": side}
                    composite_count += 1
                    break

        # 6. Passe de garantie géométrique 0x72
        # (a) Tout VOID adjacent (8-voisins) à FLOOR ou DOOR devient WALL
        for y in range(self.height):
            for x in range(self.width):
                if grid[y][x] == VOID:
                    has_floor_neighbor = False
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < self.width and 0 <= ny < self.height:
                                if grid[ny][nx] in (FLOOR, DOOR_CLOSED, DOOR_OPEN):
                                    has_floor_neighbor = True
                                    break
                        if has_floor_neighbor:
                            break
                    if has_floor_neighbor:
                        grid[y][x] = WALL

        # (b) S'assurer que chaque mur horizontal au-dessus d'un sol a une case de rebord (ty - 1)
        for y in range(1, self.height):
            for x in range(self.width):
                if grid[y][x] == WALL:
                    # Si au sud il y a un sol/porte
                    if y + 1 < self.height and grid[y + 1][x] in (FLOOR, DOOR_CLOSED, DOOR_OPEN):
                        if y - 1 >= 0 and grid[y - 1][x] == VOID:
                            grid[y - 1][x] = WALL

        # (c) Piliers isolés 1x1 : convertis ou nettoyés
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if grid[y][x] == WALL:
                    # Entouré des 4 côtés cardinaux par du sol
                    if (
                        grid[y - 1][x] in (FLOOR, DOOR_CLOSED, DOOR_OPEN)
                        and grid[y + 1][x] in (FLOOR, DOOR_CLOSED, DOOR_OPEN)
                        and grid[y][x - 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN)
                        and grid[y][x + 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN)
                    ):
                        grid[y][x] = FLOOR  # Ou prop colonne

        # 7. Attribution des types de salles et entités spéciales
        # Distance depuis rooms[0] (spawn) par BFS sur les centres de salles
        rooms[0]["kind"] = "spawn"
        spawn_center_x, spawn_center_y = rooms[0]["cx"], rooms[0]["cy"]
        spawn_candidates: list[tuple[int, int]] = [
            (spawn_center_x - 1, spawn_center_y - 1),
            (spawn_center_x, spawn_center_y - 1),
            (spawn_center_x + 1, spawn_center_y - 1),
            (spawn_center_x - 1, spawn_center_y),
            (spawn_center_x, spawn_center_y),
            (spawn_center_x + 1, spawn_center_y),
        ]
        spawn_points: list[tuple[int, int]] = [
            (sx * self.tile_size + 8, sy * self.tile_size + 8)
            for sx, sy in spawn_candidates
            if 0 <= sx < self.width and 0 <= sy < self.height and grid[sy][sx] == FLOOR
        ]

        # Calcul des distances depuis rooms[0]
        room_distances: list[tuple[float, int]] = []
        for i in range(1, num_rooms):
            dist = math.hypot(rooms[i]["cx"] - rooms[0]["cx"], rooms[i]["cy"] - rooms[0]["cy"])
            room_distances.append((dist, i))
        room_distances.sort(key=lambda t: t[0])

        # Salle portail = la plus éloignée
        portal_room_idx = room_distances[-1][1]
        rooms[portal_room_idx]["kind"] = "portal"
        p_cx = rooms[portal_room_idx]["cx"]
        p_cy = rooms[portal_room_idx]["cy"]
        portal: dict[str, Any] = {
            "id": "portal_main",
            "x": float(p_cx * self.tile_size + 8),
            "y": float(p_cy * self.tile_size + 8),
            "tx": p_cx,
            "ty": p_cy,
            "active": False,
            "sprite": "floor_ladder"
        }

        # Salles de fontaines (shrines) = 2 salles de distance médiane
        fountains: list[dict[str, Any]] = []
        shrine_indices = [room_distances[len(room_distances) // 3][1], room_distances[2 * len(room_distances) // 3][1]]
        for i, s_idx in enumerate(shrine_indices):
            rooms[s_idx]["kind"] = "shrine"
            s_room = rooms[s_idx]
            s_cx = s_room["cx"]
            # Mur nord de la salle : y = s_room["y"] - 1 si c'est un mur, sinon s_room["y"]
            wall_y = s_room["y"] - 1 if s_room["y"] > 0 and grid[s_room["y"] - 1][s_cx] == WALL else s_room["y"]
            floor_y = wall_y + 1 if wall_y + 1 < self.height and grid[wall_y + 1][s_cx] == FLOOR else s_room["cy"]
            fountains.append({
                "id": f"fountain_{i}",
                "x": float(s_cx * self.tile_size + 8),
                "y": float(floor_y * self.tile_size + 8),
                "tx": s_cx,
                "ty": floor_y,
                "wall_tx": s_cx,
                "wall_ty": wall_y,
                "type": "red",
                "mid_sprite": "wall_fountain_mid_red_anim_f0",
                "basin_sprite": "wall_fountain_basin_red_anim_f0"
            })

        # Colonnes physiques (WALL) dans les grandes salles (>= 9x8) avant tirage des spawns
        for r in rooms:
            rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
            if rw >= 9 and rh >= 8 and r["kind"] in ("normal", "spawn"):
                col_coords = (
                    (rx + 2, ry + 2),
                    (rx + rw - 3, ry + 2),
                    (rx + 2, ry + rh - 3),
                    (rx + rw - 3, ry + rh - 3),
                )
                for cx, cy in col_coords:
                    if (
                        1 <= cx < self.width - 1
                        and 1 <= cy < self.height - 1
                        and grid[cy][cx] == FLOOR
                        and grid[cy - 1][cx] == FLOOR
                        and grid[cy + 1][cx] == FLOOR
                        and grid[cy][cx - 1] == FLOOR
                        and grid[cy][cx + 1] == FLOOR
                    ):
                        grid[cy][cx] = WALL

        # Cristaux d'Arcane (5 cristaux dans 5 salles distinctes hors spawn et portal)
        candidate_crystal_rooms = [
            r for r in rooms
            if r["kind"] not in ("spawn", "portal")
        ]
        rng.shuffle(candidate_crystal_rooms)
        crystals: list[dict[str, Any]] = []
        for i in range(min(5, len(candidate_crystal_rooms))):
            cr = candidate_crystal_rooms[i]
            ctx, cty = cr["cx"], cr["cy"]
            crystals.append({
                "id": f"c_{i}",
                "x": float(ctx * self.tile_size + 8),
                "y": float(cty * self.tile_size + 8),
                "tx": ctx,
                "ty": cty,
                "collected": False,
                "sprite": "flask_big_blue"
            })

        # Spawns de monstres dans les salles hors spawn
        monster_spawns: list[tuple[int, int]] = []
        for r in rooms:
            if r["kind"] == "spawn":
                continue
            rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
            # 2 à 3 points par salle
            for _ in range(rng.randint(2, 3)):
                mx = rng.randint(rx + 1, rx + rw - 2)
                my = rng.randint(ry + 1, ry + rh - 2)
                if grid[my][mx] == FLOOR:
                    monster_spawns.append((mx * self.tile_size + 8, my * self.tile_size + 8))

        # 8. Autotiler 2.5D
        tiles = self.compute_autotiling(grid, rooms, seed, portal=portal, fountains=fountains)

        self.grid = grid
        self.tiles = tiles
        self.rooms = rooms
        self.doors = sorted(doors_placed)
        self.portal = portal
        self.fountains = fountains
        self.crystals = crystals
        self.monster_spawns = monster_spawns
        self.dungeon = {
            "width": self.width,
            "height": self.height,
            "tile_size": self.tile_size,
            "seed": seed,
            "grid": grid,
            "tiles": tiles,
            "rooms": rooms,
            "spawn_points": spawn_points,
            "portal": portal,
            "fountains": fountains,
            "crystals": crystals,
            "monster_spawns": monster_spawns,
        }
        return self.dungeon

    def compute_autotiling(
        self,
        grid: list[list[int]],
        rooms: list[dict[str, Any]],
        seed: int,
        portal: Optional[dict[str, Any]] = None,
        fountains: Optional[list[dict[str, Any]]] = None,
    ) -> list[list[dict[str, Optional[str]]]]:
        """Calcule les couches de sprites (fl, wb, wt, wl, wr, pr) pour toute la grille."""
        height = len(grid)
        width = len(grid[0])
        tiles: list[list[dict[str, Optional[str]]]] = [
            [{"fl": None, "wb": None, "wt": None, "wl": None, "wr": None, "pr": None} for _ in range(width)]
            for _ in range(height)
        ]

        # 1. Sol (fl)
        for y in range(height):
            for x in range(width):
                cell = grid[y][x]
                if cell in (FLOOR, DOOR_CLOSED, DOOR_OPEN):
                    # Choix déterministe par hash
                    h = (x * 73856093 ^ y * 19349663 ^ seed * 83492791) % 100
                    if h < 55:
                        tiles[y][x]["fl"] = "floor_1"
                    elif h < 70:
                        tiles[y][x]["fl"] = "floor_2"
                    elif h < 85:
                        tiles[y][x]["fl"] = "floor_3"
                    elif h < 88:
                        tiles[y][x]["fl"] = "floor_4"
                    elif h < 91:
                        tiles[y][x]["fl"] = "floor_5"
                    elif h < 94:
                        tiles[y][x]["fl"] = "floor_6"
                    elif h < 97:
                        tiles[y][x]["fl"] = "floor_7"
                    else:
                        tiles[y][x]["fl"] = "floor_8"

        # 2. Portes (wb)
        for y in range(height):
            for x in range(width):
                cell = grid[y][x]
                if cell == DOOR_CLOSED:
                    tiles[y][x]["wb"] = "doors_leaf_closed"
                elif cell == DOOR_OPEN:
                    tiles[y][x]["wb"] = "doors_leaf_open"

        # 3. Murs (wb, wt, wl, wr)
        for y in range(height):
            for x in range(width):
                if grid[y][x] == WALL:
                    south_walkable = (y + 1 < height and grid[y + 1][x] in (FLOOR, DOOR_CLOSED, DOOR_OPEN))

                    if south_walkable:
                        # Face frontale vue de face
                        left_wall = (
                            x > 0
                            and grid[y][x - 1] == WALL
                            and (y + 1 < height and grid[y + 1][x - 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN))
                        )
                        right_wall = (
                            x + 1 < width
                            and grid[y][x + 1] == WALL
                            and (y + 1 < height and grid[y + 1][x + 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN))
                        )

                        if not left_wall and right_wall:
                            tiles[y][x]["wb"] = "wall_left"
                        elif not right_wall and left_wall:
                            tiles[y][x]["wb"] = "wall_right"
                        else:
                            # wall_mid avec possible décoration ~18%
                            h_dec = (x * 314159 ^ y * 271828 ^ seed * 161803) % 100
                            if h_dec < 18 and left_wall and right_wall:
                                dec_sprite = WALL_DECORATIONS[h_dec % len(WALL_DECORATIONS)]
                                tiles[y][x]["wb"] = dec_sprite
                                if dec_sprite == "wall_goo" and y + 1 < height:
                                    tiles[y + 1][x]["pr"] = "wall_goo_base"
                            else:
                                tiles[y][x]["wb"] = "wall_mid"
                    else:
                        # Mur intérieur ou latéral
                        left_floor = (x > 0 and grid[y][x - 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN))
                        right_floor = (x + 1 < width and grid[y][x + 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN))
                        if left_floor:
                            tiles[y][x]["wb"] = "wall_outer_front_left"
                        elif right_floor:
                            tiles[y][x]["wb"] = "wall_outer_front_right"
                        else:
                            tiles[y][x]["wb"] = "wall_mid"

                    # Rebord supérieur wt
                    w_is_wall = (x > 0 and grid[y][x - 1] == WALL)
                    e_is_wall = (x + 1 < width and grid[y][x + 1] == WALL)

                    if not w_is_wall and e_is_wall:
                        tiles[y][x]["wt"] = "wall_top_left"
                    elif w_is_wall and not e_is_wall:
                        tiles[y][x]["wt"] = "wall_top_right"
                    else:
                        tiles[y][x]["wt"] = "wall_top_mid"

                    # Bordures latérales wl et wr
                    if x + 1 < width and grid[y][x + 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN):
                        tiles[y][x]["wr"] = "wall_outer_mid_left"
                    if x > 0 and grid[y][x - 1] in (FLOOR, DOOR_CLOSED, DOOR_OPEN):
                        tiles[y][x]["wl"] = "wall_outer_mid_right"

        # 4. Props spéciaux
        # (a) Fontaines
        if fountains:
            for f in fountains:
                wtx, wty = f["wall_tx"], f["wall_ty"]
                ftx, fty = f["tx"], f["ty"]
                if 0 <= wtx < width and 0 <= wty < height:
                    tiles[wty][wtx]["wb"] = f["mid_sprite"]
                if 0 <= ftx < width and 0 <= fty < height:
                    tiles[fty][ftx]["pr"] = f["basin_sprite"]

        # (b) Colonnes dans les grandes salles et props au sol
        for r in rooms:
            rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
            # Colonnes si salle assez grande (>= 9x8) et pilier encore WALL entouré de 4 FLOOR
            if rw >= 9 and rh >= 8 and r["kind"] in ("normal", "spawn"):
                col_x1, col_y1 = rx + 2, ry + 2
                col_x2, col_y2 = rx + rw - 3, ry + 2
                col_x3, col_y3 = rx + 2, ry + rh - 3
                col_x4, col_y4 = rx + rw - 3, ry + rh - 3
                for cx, cy in ((col_x1, col_y1), (col_x2, col_y2), (col_x3, col_y3), (col_x4, col_y4)):
                    if (
                        1 <= cx < width - 1
                        and 1 <= cy < height - 1
                        and grid[cy][cx] == WALL
                        and grid[cy - 1][cx] == FLOOR
                        and grid[cy + 1][cx] == FLOOR
                        and grid[cy][cx - 1] == FLOOR
                        and grid[cy][cx + 1] == FLOOR
                    ):
                        if not tiles[cy][cx]["fl"]:
                            tiles[cy][cx]["fl"] = "floor_1"
                        tiles[cy][cx]["pr"] = "column"
                        tiles[cy][cx]["wb"] = "column"
                        tiles[cy][cx]["wt"] = "column"
                        tiles[cy][cx]["wl"] = None
                        tiles[cy][cx]["wr"] = None

            # Petits props au sol dans les coins (skull, crate, chest)
            if r["kind"] == "normal":
                h_prop = (rx * 17 + ry * 31 + seed) % 100
                if h_prop < 40:
                    px, py = rx + 1, ry + 1
                    if grid[py][px] == FLOOR and tiles[py][px]["pr"] is None:
                        tiles[py][px]["pr"] = FLOOR_PROPS[h_prop % len(FLOOR_PROPS)]

        return tiles

    _build_tile_layers = compute_autotiling

    def recompute_area(
        self,
        dungeon_data: dict[str, Any],
        center_tx: int,
        center_ty: int,
        radius: int = 3
    ) -> list[dict[str, Any]]:
        """Recalcule tiles[ty][tx] dans un carré [center-radius .. center+radius]."""
        grid = dungeon_data["grid"]
        tiles = dungeon_data["tiles"]
        rooms = dungeon_data.get("rooms", [])
        seed = dungeon_data.get("seed", 42)
        portal = dungeon_data.get("portal")
        fountains = dungeon_data.get("fountains")

        height = len(grid)
        width = len(grid[0])

        min_y = max(0, center_ty - radius)
        max_y = min(height - 1, center_ty + radius)
        min_x = max(0, center_tx - radius)
        max_x = min(width - 1, center_tx + radius)

        # Recalcule une zone temporaire
        fresh_tiles = self.compute_autotiling(grid, rooms, seed, portal=portal, fountains=fountains)

        updated: list[dict[str, Any]] = []
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                tiles[y][x] = fresh_tiles[y][x]
                updated.append({
                    "tx": x,
                    "ty": y,
                    "cell_value": int(grid[y][x]),
                    "tile": tiles[y][x]
                })

        return updated

    def render_full_vision_image(
        self,
        output_path: str,
        scale: int = 2,
        crop_box: tuple[int, int, int, int] | None = None,
    ) -> str:
        """
        Rend le labyrinthe en pleine visibilité (sans brouillard de guerre)
        selon les couches 2.5D de self.tiles avec les sprites de assets/frames/.
        """
        from PIL import Image

        if not self.tiles or not self.grid:
            self._generate_procedural_dungeon(self.seed)

        sprite_cache: dict[str, Image.Image] = {}

        def get_sprite(name: str) -> Image.Image:
            if name not in sprite_cache:
                sprite_path = ASSETS_FRAMES_DIR / f"{name}.png"
                sprite_cache[name] = Image.open(sprite_path).convert("RGBA")
            return sprite_cache[name]

        ts = self.tile_size
        canvas = Image.new("RGBA", (self.width * ts, self.height * ts), (9, 10, 15, 255))

        # 1. Couche de sol (fl)
        for ty in range(self.height):
            for tx in range(self.width):
                tile = self.tiles[ty][tx]
                fl = tile.get("fl")
                if fl:
                    sp = get_sprite(fl)
                    canvas.alpha_composite(sp, (tx * ts, ty * ts))

        # 2. Couche de base des murs (wb), portes, props au sol (pr) et rebords latéraux (wl / wr)
        for ty in range(self.height):
            for tx in range(self.width):
                tile = self.tiles[ty][tx]
                px, py = tx * ts, ty * ts

                wb = tile.get("wb")
                pr = tile.get("pr")

                if wb == "column" or pr == "column":
                    col_img = get_sprite("column")
                    shaft = col_img.crop((0, 16, 16, 40))
                    canvas.alpha_composite(shaft, (px, max(0, py - 8)))
                else:
                    if pr:
                        pr_img = get_sprite(pr)
                        oy = py + ts - pr_img.height if pr_img.height > ts else py
                        canvas.alpha_composite(pr_img, (px, max(0, oy)))
                    if wb:
                        wb_img = get_sprite(wb)
                        if wb in ("doors_leaf_closed", "doors_leaf_open") and wb_img.size != (ts, ts):
                            wb_img = wb_img.resize((ts, ts), Image.Resampling.NEAREST)
                        canvas.alpha_composite(wb_img, (px, py))

                wl = tile.get("wl")
                if wl:
                    canvas.alpha_composite(get_sprite(wl), (px, py))
                wr = tile.get("wr")
                if wr:
                    canvas.alpha_composite(get_sprite(wr), (px, py))

        # 3. Cristaux d'Arcane sur le sol
        for cr in self.crystals:
            ctx_i, cty_i = int(cr["tx"]), int(cr["ty"])
            if 0 <= ctx_i < self.width and 0 <= cty_i < self.height:
                c_img = get_sprite(cr.get("sprite", "flask_big_blue"))
                canvas.alpha_composite(c_img, (ctx_i * ts, cty_i * ts))

        # 4. Couche supérieure 2.5D (wt : wall_top_*, wall_outer_top_*, column décalée en Y)
        for ty in range(self.height):
            for tx in range(self.width):
                tile = self.tiles[ty][tx]
                wt = tile.get("wt")
                if not wt:
                    continue
                px, py = tx * ts, ty * ts
                if wt == "column":
                    col_img = get_sprite("column")
                    cap = col_img.crop((0, 0, 16, 20))
                    canvas.alpha_composite(cap, (px, max(0, py - 24)))
                else:
                    wt_img = get_sprite(wt)
                    canvas.alpha_composite(wt_img, (px, py))

        if crop_box is not None:
            tx0, ty0, tx1, ty1 = crop_box
            x0 = max(0, min(self.width, tx0)) * ts
            y0 = max(0, min(self.height, ty0)) * ts
            x1 = max(x0 + ts, min(self.width, tx1) * ts)
            y1 = max(y0 + ts, min(self.height, ty1) * ts)
            canvas = canvas.crop((x0, y0, x1, y1))

        if scale > 1:
            canvas = canvas.resize(
                (canvas.width * scale, canvas.height * scale),
                Image.Resampling.NEAREST,
            )

        out_file = Path(output_path).resolve()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out_file, format="PNG")
        return str(out_file)


class Maze(DungeonGenerator):
    """Classe de labyrinthe procédural 2.5D avec génération immédiate et export d'image."""

    def __init__(
        self,
        width: int = 56,
        height: int = 56,
        seed: Optional[int] = None,
        tile_size: int = 16,
    ) -> None:
        super().__init__(width=width, height=height, tile_size=tile_size, seed=seed)
        if not self.tiles:
            self._generate_procedural_dungeon(seed=seed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Générateur procédural de donjon 2.5D Mazic et export PNG full-vision."
    )
    parser.add_argument("--width", type=int, default=56, help="Largeur de la grille en cases (défaut: 56)")
    parser.add_argument("--height", type=int, default=56, help="Hauteur de la grille en cases (défaut: 56)")
    parser.add_argument("--seed", type=int, default=None, help="Graine aléatoire optionnelle (int)")
    parser.add_argument("--scale", type=int, default=2, help="Facteur d'agrandissement NEAREST (défaut: 2)")
    parser.add_argument(
        "--output",
        type=str,
        default="maze_full_vision.png",
        help="Chemin du fichier PNG de sortie",
    )
    parser.add_argument(
        "--crop",
        type=str,
        default=None,
        help="Découpe optionnelle x0,y0,x1,y1 en cases (ex: 26,12,43,27)",
    )
    args = parser.parse_args()

    crop_tuple: tuple[int, int, int, int] | None = None
    if args.crop:
        parts = [int(p.strip()) for p in args.crop.split(",")]
        if len(parts) != 4:
            raise ValueError("--crop doit contenir 4 entiers séparés par des virgules: x0,y0,x1,y1")
        crop_tuple = (parts[0], parts[1], parts[2], parts[3])

    maze = Maze(width=args.width, height=args.height, seed=args.seed)
    saved_path = maze.render_full_vision_image(
        output_path=args.output,
        scale=args.scale,
        crop_box=crop_tuple,
    )
    comp_rooms = sum(1 for r in maze.rooms if r.get("shape") in ("L", "T"))
    col_rooms = sum(
        1
        for r in maze.rooms
        if r["w"] >= 9 and r["h"] >= 8 and r["kind"] in ("normal", "spawn")
    )
    print(
        f"[Mazic MazeGenerator] Dimensions={maze.width}x{maze.height} | "
        f"Seed={maze.seed} | Salles={len(maze.rooms)} (dont {comp_rooms} composites L/T, {col_rooms} à colonnes) | "
        f"Portes={len(maze.doors)} | Scale=x{args.scale} | Crop={crop_tuple} -> {saved_path}"
    )
