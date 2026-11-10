"""
Moteur de jeu serveur autoritaire 30 Hz - Mazic.
Gère la physique AABB, le raycasting DDA, le pathfinding A*,
la machine à états IA 'Chasseur Honnête', les sorts et l'esprit de ruche.
"""

from __future__ import annotations

import heapq
import math
import random
import time
from dataclasses import dataclass, field
from typing import Any

from server.maze_generator import (
    DOOR_CLOSED,
    DOOR_OPEN,
    FLOOR,
    VOID,
    WALL,
    DungeonGenerator,
)

TILE_SIZE = 16

HERO_SKINS = [
    "wizzard_m",
    "wizzard_f",
    "knight_m",
    "knight_f",
    "elf_m",
    "elf_f",
    "lizard_m",
    "lizard_f",
]

MONSTER_SKINS = ["chort", "skelet", "big_zombie", "masked_orc", "imp", "tiny_zombie"]
MONSTER_PLAYER_SKIN = "big_demon"

# Types de monstres IA actuellement activés en jeu.
# Statistiques de base FIXES : elles n'augmentent pas avec le temps.
# (La vitesse est modulée uniquement par l'état IA : PATROL 42 / SEARCH 50 / CHASE 76.)
MONSTER_TYPES: dict[str, dict[str, Any]] = {
    "hunter": {
        "skin": "chort",
        "hp": 100.0,
        "speed": 42.0,
        "unlock_kills": 0,
        "base_weight": 1.0,
    },
}

# Apparition continue des monstres IA (style Zombie Wars)
MONSTER_SPAWN_INTERVAL = 15.0  # secondes entre deux apparitions
MONSTER_SPAWN_MIN_TILES = 12  # distance minimale (en cases) à tout humain vivant
MAX_ACTIVE_AI_MONSTERS = 14  # plafond de monstres IA simultanés
INITIAL_AI_MONSTERS = 4

# Joueur-Monstre abattu : réapparition éloignée + étourdissement
PLAYER_MONSTER_RESPAWN_STUN = 4.0

# Déplacement au clic droit (style LoL)
MOVE_TARGET_ARRIVAL_PX = 3.0
MOVING_SPEED_THRESHOLD = 2.0


def is_cell_blocking(grid: list[list[int]], tx: int, ty: int) -> bool:
    """Vérifie si une tuile de la grille bloque le passage et la vue."""
    if ty < 0 or ty >= len(grid) or tx < 0 or tx >= len(grid[0]):
        return True
    return grid[ty][tx] in (VOID, WALL, DOOR_CLOSED)


def check_box_collision(
    grid: list[list[int]], cx: float, cy: float, r: float = 5.5
) -> bool:
    """Vérifie si une boîte englobante AABB (rayon r) touche un mur ou le vide."""
    min_tx = int((cx - r) // TILE_SIZE)
    max_tx = int((cx + r) // TILE_SIZE)
    min_ty = int((cy - r) // TILE_SIZE)
    max_ty = int((cy + r) // TILE_SIZE)

    for ty in range(min_ty, max_ty + 1):
        for tx in range(min_tx, max_tx + 1):
            if is_cell_blocking(grid, tx, ty):
                return True
    return False


def move_entity_with_collision(
    grid: list[list[int]],
    x: float,
    y: float,
    vx: float,
    vy: float,
    dt: float,
    r: float = 5.5,
) -> tuple[float, float, bool]:
    """
    Déplace une entité avec collision AABB stricte et glissement sur les murs.
    Teste séparément l'axe X puis l'axe Y pour empêcher le passage à travers les murs.
    """
    dx = vx * dt
    dy = vy * dt
    collided = False

    # Test déplacement X
    new_x = x + dx
    if check_box_collision(grid, new_x, y, r):
        collided = True
        new_x = x

    # Test déplacement Y
    new_y = y + dy
    if check_box_collision(grid, new_x, new_y, r):
        collided = True
        new_y = y

    return new_x, new_y, collided


def has_line_of_sight(
    grid: list[list[int]],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> tuple[bool, int]:
    """
    Raycasting DDA serveur (Amanatides & Woo) sur la grille 16x16.
    Compte le nombre de murs/portes fermées traversés.
    Retourne (wall_count == 0, wall_count).
    """
    tx0 = int(x0 // TILE_SIZE)
    ty0 = int(y0 // TILE_SIZE)
    tx1 = int(x1 // TILE_SIZE)
    ty1 = int(y1 // TILE_SIZE)

    if tx0 == tx1 and ty0 == ty1:
        c = 1 if is_cell_blocking(grid, tx0, ty0) else 0
        return (c == 0, c)

    dx = x1 - x0
    dy = y1 - y0

    step_x = 1 if dx > 0 else (-1 if dx < 0 else 0)
    step_y = 1 if dy > 0 else (-1 if dy < 0 else 0)

    t_delta_x = abs(float(TILE_SIZE) / dx) if dx != 0 else float("inf")
    t_delta_y = abs(float(TILE_SIZE) / dy) if dy != 0 else float("inf")

    if dx > 0:
        t_max_x = ((tx0 + 1) * TILE_SIZE - x0) / dx
    elif dx < 0:
        t_max_x = (x0 - tx0 * TILE_SIZE) / (-dx)
    else:
        t_max_x = float("inf")

    if dy > 0:
        t_max_y = ((ty0 + 1) * TILE_SIZE - y0) / dy
    elif dy < 0:
        t_max_y = (y0 - ty0 * TILE_SIZE) / (-dy)
    else:
        t_max_y = float("inf")

    tx, ty = tx0, ty0
    wall_count = 0
    max_iters = 250
    iters = 0

    while (tx != tx1 or ty != ty1) and iters < max_iters:
        iters += 1
        if t_max_x < t_max_y:
            t_max_x += t_delta_x
            tx += step_x
        else:
            t_max_y += t_delta_y
            ty += step_y

        if is_cell_blocking(grid, tx, ty):
            wall_count += 1

    return (wall_count == 0, wall_count)


def astar_grid_path(
    grid: list[list[int]],
    start: tuple[int, int],
    target: tuple[int, int],
    max_steps: int = 350,
) -> list[tuple[int, int]]:
    """
    Pathfinding A* sur la grille de tuiles (FLOOR ou DOOR_OPEN uniquement).
    Retourne la liste des étapes [(tx0, ty0), (tx1, ty1), ...].
    """
    if start == target:
        return [start]

    # Si la cible est bloquée, trouver la case praticable adjacente la plus proche
    if is_cell_blocking(grid, target[0], target[1]):
        neighbors = [
            (target[0] + dx, target[1] + dy)
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0))
            if not is_cell_blocking(grid, target[0] + dx, target[1] + dy)
        ]
        if not neighbors:
            return []
        target = min(neighbors, key=lambda p: abs(p[0] - start[0]) + abs(p[1] - start[1]))

    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set: list[tuple[float, float, tuple[int, int]]] = []
    heapq.heappush(open_set, (heuristic(start, target), 0.0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    closed_set: set[tuple[int, int]] = set()

    steps = 0
    while open_set and steps < max_steps:
        steps += 1
        _, current_g, current = heapq.heappop(open_set)

        if current == target:
            # Reconstitution du chemin
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        closed_set.add(current)

        cx, cy = current
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nxt = (cx + dx, cy + dy)
            if is_cell_blocking(grid, nxt[0], nxt[1]) or nxt in closed_set:
                continue

            tentative_g = current_g + 1.0
            if tentative_g < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative_g
                f = tentative_g + heuristic(nxt, target)
                heapq.heappush(open_set, (f, tentative_g, nxt))

    return []


@dataclass
class PlayerState:
    id: str
    name: str
    skin: str = "wizzard_m"
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    aim_angle: float = 0.0
    facing_left: bool = False
    anim: str = "idle"
    hp: float = 100.0
    max_hp: float = 100.0
    mana: float = 100.0
    max_mana: float = 100.0
    is_monster: bool = False
    monster_skin: str = MONSTER_PLAYER_SKIN
    sneak: bool = False
    mic_rms: float = 0.0
    noise_radius: float = 0.0
    noise_event_timer: float = 0.0
    arcane_sight_until: float = 0.0
    stun_until: float = 0.0
    # Déplacement au clic droit (style LoL) et visée souris à l'arrêt
    move_target_x: float = 0.0
    move_target_y: float = 0.0
    has_move_target: bool = False
    mouse_aim_angle: float = 0.0
    # Score de survie : score = survie - temps monstre pendant que d'autres humains vivaient
    survival_time: float = 0.0
    monster_active_time: float = 0.0
    score: float = 0.0
    spell_cooldowns: dict[str, float] = field(default_factory=lambda: {
        "attack": 0.0,
        "1": 0.0,
        "2": 0.0,
        "3": 0.0,
        "4": 0.0,
        "interact": 0.0,
        "respawn": 0.0,
    })

    def clear_move_target(self) -> None:
        """Annule l'ordre de marche et immobilise immédiatement le joueur."""
        self.has_move_target = False
        self.vx = 0.0
        self.vy = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "skin": self.monster_skin if self.is_monster else self.skin,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "vx": round(self.vx, 2),
            "vy": round(self.vy, 2),
            "aim_angle": round(self.aim_angle, 3),
            "facing_left": self.facing_left,
            "anim": self.anim,
            "hp": round(self.hp, 1),
            "max_hp": round(self.max_hp, 1),
            "mana": round(self.mana, 1),
            "max_mana": round(self.max_mana, 1),
            "is_monster": self.is_monster,
            "sneak": self.sneak,
            "mic_rms": round(self.mic_rms, 3),
            "noise_radius": round(self.noise_radius, 1),
            "arcane_sight_active": self.arcane_sight_until > time.time(),
            "is_stunned": self.stun_until > time.time(),
            "cooldowns": {k: round(max(0.0, v), 2) for k, v in self.spell_cooldowns.items()},
            "has_move_target": self.has_move_target,
            "move_target_x": round(self.move_target_x, 2),
            "move_target_y": round(self.move_target_y, 2),
            "survival_time": round(self.survival_time, 1),
            "monster_active_time": round(self.monster_active_time, 1),
            "score": round(self.score, 1),
        }


@dataclass
class MonsterState:
    id: str
    name: str
    skin: str = "chort"
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    aim_angle: float = 0.0
    facing_left: bool = False
    anim: str = "idle"
    hp: float = 100.0
    max_hp: float = 100.0
    monster_type: str = "hunter"
    state: str = "PATROL"  # PATROL, CHASE, SEARCH
    last_known_pos: tuple[float, float] | None = None
    target_player_id: str | None = None
    path: list[tuple[int, int]] = field(default_factory=list)
    repath_cd: float = 0.0
    search_timer: float = 0.0
    search_targets: list[tuple[int, int]] = field(default_factory=list)
    attack_cd: float = 0.0
    patrol_target: tuple[int, int] | None = None
    patrol_idle_timer: float = 0.0
    speed: float = 42.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "skin": self.skin,
            "monster_type": self.monster_type,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "vx": round(self.vx, 2),
            "vy": round(self.vy, 2),
            "aim_angle": round(self.aim_angle, 3),
            "facing_left": self.facing_left,
            "anim": self.anim,
            "hp": round(self.hp, 1),
            "max_hp": round(self.max_hp, 1),
            "state": self.state,
            "target_player_id": self.target_player_id,
        }


@dataclass
class ProjectileState:
    id: str
    owner_id: str
    x: float
    y: float
    vx: float
    vy: float
    radius: float = 4.0
    damage: float = 45.0
    kind: str = "fireball"
    life: float = 2.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "vx": round(self.vx, 2),
            "vy": round(self.vy, 2),
            "angle": round(math.atan2(self.vy, self.vx), 3),
            "kind": self.kind,
            "skin": "FB001" if self.kind == "fireball" else "weapon_red_magic_staff",
        }


class GameRoom:
    """Moteur de salle autoritaire 30 Hz côté serveur."""

    def __init__(self, room_id: str = "default", dungeon: dict[str, Any] | None = None) -> None:
        self.room_id = room_id
        if dungeon is not None:
            self.dungeon = dungeon
        else:
            self.dungeon = DungeonGenerator().generate()

        self.grid: list[list[int]] = self.dungeon["grid"]
        self.width: int = len(self.grid[0])
        self.height: int = len(self.grid)

        self.players: dict[str, PlayerState] = {}
        self.monsters: list[MonsterState] = []
        self.projectiles: list[ProjectileState] = []

        self.pending_tile_updates: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []

        # Mode Survie Pure : aucun cristal ni portail, les joueurs sont condamnés à perdre.
        # Le but est de survivre le plus longtemps possible (cf. PlayerState.score).
        self.fountains: list[dict[str, Any]] = self.dungeon.get("fountains", [])
        self.game_status: str = "RUNNING"  # RUNNING, GAME_OVER
        self.projectile_seq: int = 0
        self.monster_seq: int = 0
        self.monsters_killed: int = 0
        self.monster_spawn_timer: float = MONSTER_SPAWN_INTERVAL
        # Classement figé au passage en GAME_OVER (None tant que la partie tourne)
        self.final_ranking: list[dict[str, Any]] | None = None

        self.generator = DungeonGenerator(self.width, self.height)
        self._spawn_initial_monsters()

    def get_init_payload(self) -> dict[str, Any]:
        """Retourne les données du donjon pour l'initialisation client."""
        return self.dungeon

    def _recompute_area(self, tx: int, ty: int, radius: int = 2) -> list[dict[str, Any]]:
        """Recalcule l'autotiling autour d'une case modifiée."""
        return self.generator.recompute_area(self.dungeon, tx, ty, radius=radius)

    def choose_next_monster_type(self) -> str:
        """
        Choisit le type du prochain monstre IA selon des poids probabilistes
        dépendant du nombre de monstres déjà éliminés (`self.monsters_killed`).

        Seuls les types présents dans `MONSTER_TYPES` dont le palier
        `unlock_kills` est atteint participent au tirage.

        Paliers futurs prévus (NON activés tant qu'ils ne sont pas ajoutés à MONSTER_TYPES) :
          - 10 kills : « Rôdeur » (skin `skelet`), rapide mais fragile ;
          - 25 kills : « Brute » (skin `big_zombie`), lente, très résistante ;
          - 45 kills : « Chaman » (skin `masked_orc`), sorts à distance.
        Leur poids croîtra avec `monsters_killed` au-delà de leur palier, celui du
        Chasseur de base décroissant d'autant.

        Tant que seul le Chasseur Honnête est activé, retourne toujours `"hunter"`
        (skin `chort`).
        """
        unlocked = [
            name for name, spec in MONSTER_TYPES.items()
            if self.monsters_killed >= spec["unlock_kills"]
        ]
        if not unlocked:
            raise RuntimeError(
                f"Aucun type de monstre débloqué pour monsters_killed={self.monsters_killed}"
            )
        weights = [MONSTER_TYPES[name]["base_weight"] for name in unlocked]
        return random.choices(unlocked, weights=weights, k=1)[0]

    def _create_monster(self, monster_type: str, x: float, y: float) -> MonsterState:
        """Instancie un monstre IA du type demandé avec ses statistiques de base fixes."""
        spec = MONSTER_TYPES[monster_type]
        self.monster_seq += 1
        m = MonsterState(
            id=f"m_{self.monster_seq}",
            name=f"Monster {self.monster_seq}",
            skin=spec["skin"],
            x=float(x),
            y=float(y),
            hp=spec["hp"],
            max_hp=spec["hp"],
            monster_type=monster_type,
            state="PATROL",
            speed=spec["speed"],
        )
        self.monsters.append(m)
        return m

    def _spawn_initial_monsters(self) -> None:
        """
        Fait apparaître les Chasseurs initiaux sur des points de spawn distincts,
        à au moins MONSTER_SPAWN_MIN_TILES cases de tout point d'apparition joueur
        (même règle que l'apparition continue : pas de monstre collé au départ).
        """
        spawns = self.dungeon.get("monster_spawns", [])
        player_spawns = self.dungeon.get("spawn_points", [])
        if not spawns or not player_spawns:
            raise ValueError("Le donjon généré doit contenir 'monster_spawns' et 'spawn_points'.")

        min_px = MONSTER_SPAWN_MIN_TILES * TILE_SIZE
        far_spawns = [
            (mx, my) for mx, my in spawns
            if min(math.hypot(mx - sx, my - sy) for sx, sy in player_spawns) >= min_px
        ]
        if len(far_spawns) < INITIAL_AI_MONSTERS:
            raise ValueError(
                f"Seulement {len(far_spawns)} monster_spawns à >= {MONSTER_SPAWN_MIN_TILES} cases "
                f"du départ (requis : {INITIAL_AI_MONSTERS})."
            )

        for sx, sy in random.sample(far_spawns, INITIAL_AI_MONSTERS):
            self._create_monster(self.choose_next_monster_type(), sx, sy)

    def _living_humans(self) -> list[PlayerState]:
        """Joueurs humains encore en vie."""
        return [p for p in self.players.values() if not p.is_monster and p.hp > 0]

    def _find_far_spawn_position(self) -> tuple[float, float, float | None] | None:
        """
        Cherche une case de sol libre à au moins MONSTER_SPAWN_MIN_TILES cases
        de tout humain vivant. Retourne (x, y, distance_min_en_cases) — distance
        None s'il n'y a plus aucun humain vivant — ou None si aucune case du
        donjon ne satisfait la contrainte.
        """
        humans = self._living_humans()
        min_px = MONSTER_SPAWN_MIN_TILES * TILE_SIZE
        candidates: list[tuple[float, float, float | None]] = []
        for ty in range(self.height):
            for tx in range(self.width):
                if self.grid[ty][tx] != FLOOR:
                    continue
                cx = tx * TILE_SIZE + 8.0
                cy = ty * TILE_SIZE + 8.0
                if check_box_collision(self.grid, cx, cy, r=5.5):
                    continue
                if not humans:
                    candidates.append((cx, cy, None))
                    continue
                d = min(math.hypot(h.x - cx, h.y - cy) for h in humans)
                if d >= min_px:
                    candidates.append((cx, cy, d / TILE_SIZE))
        if not candidates:
            return None
        return random.choice(candidates)

    def _update_monster_spawning(self, dt: float) -> None:
        """Apparition continue d'un monstre IA toutes les MONSTER_SPAWN_INTERVAL secondes."""
        self.monster_spawn_timer -= dt
        if self.monster_spawn_timer > 0:
            return
        self.monster_spawn_timer = MONSTER_SPAWN_INTERVAL

        alive_ai = sum(1 for m in self.monsters if m.hp > 0)
        if alive_ai >= MAX_ACTIVE_AI_MONSTERS:
            return

        pos = self._find_far_spawn_position()
        if pos is None:
            # Règle de jeu explicite : on ne fait jamais apparaître un monstre à
            # moins de 12 cases d'un humain. Le cycle est sauté et signalé.
            self.events.append({
                "type": "monster_spawn_skipped",
                "reason": f"aucune case à >= {MONSTER_SPAWN_MIN_TILES} cases des humains",
            })
            return

        sx, sy, _ = pos
        m = self._create_monster(self.choose_next_monster_type(), sx, sy)
        self.events.append({
            "type": "monster_spawned",
            "monster_id": m.id,
            "monster_type": m.monster_type,
            "x": m.x,
            "y": m.y,
        })

    def _respawn_player_monster(self, player: PlayerState) -> None:
        """
        Un Joueur-Monstre abattu ne meurt pas : il réapparaît loin des humains,
        PV restaurés, étourdi PLAYER_MONSTER_RESPAWN_STUN secondes.
        """
        pos = self._find_far_spawn_position()
        if pos is not None:
            nx, ny, dist_tiles = pos
            far_enough = True
        else:
            # Aucune case à >= 12 cases : on prend explicitement la case de sol la
            # plus éloignée de tous les humains (signalé dans l'événement).
            humans = self._living_humans()
            best: tuple[float, float, float] | None = None
            for ty in range(self.height):
                for tx in range(self.width):
                    if self.grid[ty][tx] != FLOOR:
                        continue
                    cx = tx * TILE_SIZE + 8.0
                    cy = ty * TILE_SIZE + 8.0
                    if check_box_collision(self.grid, cx, cy, r=5.5):
                        continue
                    d = min(math.hypot(h.x - cx, h.y - cy) for h in humans)
                    if best is None or d > best[2]:
                        best = (cx, cy, d)
            if best is None:
                raise RuntimeError("Aucune case de sol libre pour la réapparition du Joueur-Monstre.")
            nx, ny, dist_tiles = best[0], best[1], best[2] / TILE_SIZE
            far_enough = False

        player.x = nx
        player.y = ny
        player.hp = player.max_hp
        player.clear_move_target()
        player.stun_until = time.time() + PLAYER_MONSTER_RESPAWN_STUN
        player.spell_cooldowns["respawn"] = PLAYER_MONSTER_RESPAWN_STUN
        self.events.append({
            "type": "player_monster_respawn",
            "player_id": player.id,
            "x": nx,
            "y": ny,
            "distance_tiles": round(dist_tiles, 1) if dist_tiles is not None else None,
            "min_distance_met": far_enough,
        })

    def add_player(self, player_id: str, name: str, skin: str = "wizzard_m") -> PlayerState:
        """Ajoute un joueur à la partie sur l'un des points de réapparition."""
        spawn_points = self.dungeon.get("spawn_points", [(160.0, 160.0)])
        idx = len(self.players) % len(spawn_points)
        sx, sy = spawn_points[idx]

        if skin not in HERO_SKINS:
            skin = HERO_SKINS[len(self.players) % len(HERO_SKINS)]

        player = PlayerState(
            id=player_id,
            name=name,
            skin=skin,
            x=float(sx),
            y=float(sy),
        )
        self.players[player_id] = player
        self.events.append({"type": "player_joined", "player_id": player_id, "name": name})
        return player

    def remove_player(self, player_id: str) -> None:
        """Retire un joueur déconnecté."""
        if player_id in self.players:
            del self.players[player_id]
            self.events.append({"type": "player_left", "player_id": player_id})

    def handle_player_input(self, player_id: str, data: dict[str, Any]) -> None:
        """Reçoit et applique l'entrée d'un joueur client."""
        player = self.players.get(player_id)
        if not player:
            return

        now = time.time()
        if player.stun_until > now:
            player.clear_move_target()
            player.anim = "hit"
            return

        # Visée souris (utilisée pour la lampe torche uniquement à l'arrêt, cf. step())
        if "aim_angle" in data:
            player.mouse_aim_angle = float(data["aim_angle"])
        player.sneak = bool(data.get("sneak", False))
        player.mic_rms = max(0.0, min(1.0, float(data.get("mic_rms", 0.0))))

        # Déplacement au clic droit (style LoL) : la touche S / Espace annule l'ordre.
        if data.get("stop"):
            player.clear_move_target()
        elif "move_target_x" in data and "move_target_y" in data:
            world_w = float(self.width * TILE_SIZE)
            world_h = float(self.height * TILE_SIZE)
            player.move_target_x = max(0.0, min(world_w, float(data["move_target_x"])))
            player.move_target_y = max(0.0, min(world_h, float(data["move_target_y"])))
            player.has_move_target = True

        # Actions (supporte 'attack' et 'action_attack', 'spell' et 'action_spell', 'interact' et 'action_interact')
        if data.get("attack") or data.get("action_attack"):
            self._handle_attack(player)

        spell_id = data.get("spell") or data.get("action_spell")
        if spell_id in (1, 2, 3, 4, "1", "2", "3", "4"):
            self.cast_spell(player.id, int(spell_id))

        if data.get("interact") or data.get("action_interact"):
            self._handle_interaction(player)

    handle_input = handle_player_input

    def _player_max_speed(self, player: PlayerState) -> float:
        """Vitesse maximale du joueur selon son statut."""
        if player.is_monster:
            return 92.0
        if player.sneak:
            return 42.0
        return 76.0

    def _update_player_movement(self, player: PlayerState, dt: float, now: float) -> None:
        """
        Déplacement vers la cible du clic droit avec glissement AABB, puis couplage
        de la lampe torche : en marche elle suit la direction de marche, à l'arrêt
        elle suit le curseur de la souris.
        """
        stunned = player.stun_until > now
        if stunned:
            player.vx = 0.0
            player.vy = 0.0
        elif player.has_move_target:
            dx = player.move_target_x - player.x
            dy = player.move_target_y - player.y
            dist = math.hypot(dx, dy)
            if dist <= MOVE_TARGET_ARRIVAL_PX:
                player.clear_move_target()
            else:
                # Ne pas dépasser la cible lors du dernier tick
                speed = min(self._player_max_speed(player), dist / dt)
                player.vx = (dx / dist) * speed
                player.vy = (dy / dist) * speed
        else:
            player.vx = 0.0
            player.vy = 0.0

        if not stunned and (player.vx != 0.0 or player.vy != 0.0):
            old_x, old_y = player.x, player.y
            new_x, new_y, collided = move_entity_with_collision(
                self.grid, player.x, player.y, player.vx, player.vy, dt, r=5.5
            )
            player.x = new_x
            player.y = new_y
            # Bloqué net contre un mur (aucun glissement possible) : l'ordre de marche est abandonné.
            if collided and math.hypot(new_x - old_x, new_y - old_y) < 0.05:
                player.clear_move_target()

        moving = math.hypot(player.vx, player.vy) > MOVING_SPEED_THRESHOLD
        if moving:
            player.aim_angle = math.atan2(player.vy, player.vx)
            if abs(player.vx) > 0.1:
                player.facing_left = player.vx < 0
            player.anim = "run"
        else:
            player.aim_angle = player.mouse_aim_angle
            player.facing_left = math.cos(player.aim_angle) < 0
            player.anim = "hit" if stunned else "idle"

    def _handle_attack(self, player: PlayerState) -> None:
        """Attaque de base (clic gauche)."""
        if not player.is_monster:
            # Règle Mazic : l'attaque de base d'un mage ne se tire QU'À L'ARRÊT.
            # Tout clic gauche en marche annule d'abord l'ordre de marche (même si
            # l'attaque est en recharge ou si le mana manque) et oriente le mage
            # vers le curseur.
            player.clear_move_target()
            player.aim_angle = player.mouse_aim_angle
            player.facing_left = math.cos(player.aim_angle) < 0
            player.anim = "idle"

        cd = player.spell_cooldowns.get("attack", 0.0)
        if cd > 0:
            return

        if player.is_monster:
            # Monstre joueur : coup de griffe sauvage au corps à corps
            player.spell_cooldowns["attack"] = 0.8
            self.events.append({"type": "claw_attack", "player_id": player.id, "x": player.x, "y": player.y})
            for target in self.players.values():
                if target.id != player.id and not target.is_monster and target.hp > 0:
                    dist = math.hypot(target.x - player.x, target.y - player.y)
                    if dist <= 24.0:
                        target.hp -= 28.0
                        self.events.append({
                            "type": "hit",
                            "attacker_id": player.id,
                            "target_id": target.id,
                            "damage": 28.0,
                            "x": target.x,
                            "y": target.y,
                        })
                        if target.hp <= 0:
                            self._transform_player_to_monster(target)
        else:
            # Humain : petit trait d'énergie rapide, tiré immobile (cf. ci-dessus).
            if player.mana < 10.0:
                return
            if player.has_move_target or player.vx != 0.0 or player.vy != 0.0:
                raise RuntimeError(f"Attaque de base tirée en mouvement par {player.id}")
            player.mana -= 10.0
            player.spell_cooldowns["attack"] = 0.45
            self.projectile_seq += 1
            proj = ProjectileState(
                id=f"proj_{self.projectile_seq}",
                owner_id=player.id,
                x=player.x,
                y=player.y,
                vx=math.cos(player.aim_angle) * 230.0,
                vy=math.sin(player.aim_angle) * 230.0,
                radius=3.5,
                damage=18.0,
                kind="energy_bolt",
                life=0.45,
            )
            self.projectiles.append(proj)
            self.events.append({
                "type": "spell_cast",
                "spell": "energy_bolt",
                "player_id": player.id,
                "x": player.x,
                "y": player.y,
            })

    def cast_spell(self, player_id: str, spell_id: int) -> bool:
        """Lance l'un des 4 sorts du joueur."""
        player = self.players.get(player_id)
        if not player or player.is_monster:
            return False

        now = time.time()
        key = str(spell_id)
        if player.spell_cooldowns.get(key, 0.0) > 0:
            return False

        if spell_id == 1:
            # Sort 1 : Orbe Pyrique (20 mana, cd 1.2s)
            if player.mana < 20.0:
                return False
            player.mana -= 20.0
            player.spell_cooldowns["1"] = 1.2
            player.noise_radius = max(player.noise_radius, 150.0)
            player.noise_event_timer = 0.35
            self.projectile_seq += 1
            proj = ProjectileState(
                id=f"FB_{self.projectile_seq:03d}",
                owner_id=player.id,
                x=player.x,
                y=player.y,
                vx=math.cos(player.aim_angle) * 190.0,
                vy=math.sin(player.aim_angle) * 190.0,
                radius=4.5,
                damage=45.0,
                kind="fireball",
                life=2.0,
            )
            self.projectiles.append(proj)
            self.events.append({
                "type": "spell_cast",
                "spell": "fireball",
                "player_id": player.id,
                "x": player.x,
                "y": player.y,
            })
            return True

        elif spell_id == 2:
            # Sort 2 : Brise-Mur / Barricade Runique (30 mana, cd 2.0s)
            if player.mana < 30.0:
                return False

            tx = int((player.x + math.cos(player.aim_angle) * 20.0) // TILE_SIZE)
            ty = int((player.y + math.sin(player.aim_angle) * 20.0) // TILE_SIZE)

            # Hors bordure extérieure
            if not (1 <= tx < self.width - 1 and 1 <= ty < self.height - 1):
                return False

            current_tile = self.grid[ty][tx]
            if current_tile == WALL:
                self.grid[ty][tx] = FLOOR
                player.mana -= 30.0
                player.spell_cooldowns["2"] = 2.0
                player.noise_radius = max(player.noise_radius, 150.0)
                player.noise_event_timer = 0.35
                updated = self._recompute_area(tx, ty, radius=2)
                self.pending_tile_updates.extend(updated)
                self.events.append({"type": "wall_broken", "tx": tx, "ty": ty, "player_id": player.id})
                return True
            elif current_tile == FLOOR:
                # Vérifier qu'aucune entité n'est dessus
                for p in self.players.values():
                    if math.hypot(p.x - (tx * 16 + 8), p.y - (ty * 16 + 8)) < 11.0:
                        return False
                for m in self.monsters:
                    if math.hypot(m.x - (tx * 16 + 8), m.y - (ty * 16 + 8)) < 11.0:
                        return False

                self.grid[ty][tx] = WALL
                player.mana -= 30.0
                player.spell_cooldowns["2"] = 2.0
                player.noise_radius = max(player.noise_radius, 150.0)
                player.noise_event_timer = 0.35
                updated = self._recompute_area(tx, ty, radius=2)
                self.pending_tile_updates.extend(updated)
                self.events.append({"type": "wall_built", "tx": tx, "ty": ty, "player_id": player.id})
                return True
            return False

        elif spell_id == 3:
            # Sort 3 : Clairvoyance d'Éther (25 mana, cd 8.0s)
            if player.mana < 25.0:
                return False
            player.mana -= 25.0
            player.spell_cooldowns["3"] = 8.0
            player.arcane_sight_until = now + 5.0
            player.noise_radius = max(player.noise_radius, 150.0)
            player.noise_event_timer = 0.35
            self.events.append({"type": "arcane_sight", "player_id": player.id})
            return True

        elif spell_id == 4:
            # Sort 4 : Saut Astral (35 mana, cd 5.0s)
            if player.mana < 35.0:
                return False

            max_dist = 72.0  # 4.5 cases
            steps = 24
            best_x = player.x
            best_y = player.y

            cos_a = math.cos(player.aim_angle)
            sin_a = math.sin(player.aim_angle)

            for s in range(1, steps + 1):
                cur_dist = (max_dist / steps) * s
                test_x = player.x + cos_a * cur_dist
                test_y = player.y + sin_a * cur_dist
                if check_box_collision(self.grid, test_x, test_y, r=5.5):
                    break
                best_x = test_x
                best_y = test_y

            player.x = best_x
            player.y = best_y
            # Le saut astral remplace l'ordre de marche en cours
            player.clear_move_target()
            player.mana -= 35.0
            player.spell_cooldowns["4"] = 5.0
            player.noise_radius = max(player.noise_radius, 150.0)
            player.noise_event_timer = 0.35
            self.events.append({"type": "astral_jump", "player_id": player.id, "x": best_x, "y": best_y})
            return True

        return False

    def _handle_interaction(self, player: PlayerState) -> None:
        """Interaction touche [E] : bascule de porte ou fontaine runique."""
        if player.spell_cooldowns.get("interact", 0.0) > 0:
            return
        player.spell_cooldowns["interact"] = 0.35

        ptx = int(player.x // TILE_SIZE)
        pty = int(player.y // TILE_SIZE)

        # 1. Vérifier les portes adjacentes (< 28 px)
        toggled = False
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                tx = ptx + dx
                ty = pty + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    tile = self.grid[ty][tx]
                    tile_center_x = tx * 16 + 8
                    tile_center_y = ty * 16 + 8
                    if math.hypot(tile_center_x - player.x, tile_center_y - player.y) <= 28.0:
                        if tile == DOOR_CLOSED:
                            self.grid[ty][tx] = DOOR_OPEN
                            updated = self._recompute_area(tx, ty, radius=2)
                            self.pending_tile_updates.extend(updated)
                            player.noise_radius = max(player.noise_radius, 150.0)
                            player.noise_event_timer = 0.35
                            self.events.append({
                                "type": "door_open",
                                "tx": tx,
                                "ty": ty,
                                "x": tile_center_x,
                                "y": tile_center_y,
                                "player_id": player.id,
                            })
                            toggled = True
                            break
                        elif tile == DOOR_OPEN:
                            self.grid[ty][tx] = DOOR_CLOSED
                            updated = self._recompute_area(tx, ty, radius=2)
                            self.pending_tile_updates.extend(updated)
                            player.noise_radius = max(player.noise_radius, 150.0)
                            player.noise_event_timer = 0.35
                            self.events.append({
                                "type": "door_close",
                                "tx": tx,
                                "ty": ty,
                                "x": tile_center_x,
                                "y": tile_center_y,
                                "player_id": player.id,
                            })
                            toggled = True
                            break
            if toggled:
                break

        # 2. Vérifier les fontaines runiques (< 28 px)
        for f in self.fountains:
            fx = f.get("x", 0.0)
            fy = f.get("y", 0.0)
            if math.hypot(fx - player.x, fy - player.y) <= 28.0:
                player.hp = min(player.max_hp, player.hp + 50.0)
                player.mana = min(player.max_mana, player.mana + 50.0)
                self.events.append({"type": "fountain_drink", "player_id": player.id})
                break

    def _transform_player_to_monster(self, player: PlayerState) -> None:
        """Transforme définitivement un joueur humain mort en Monstre Immortel Joueur."""
        player.is_monster = True
        player.hp = 160.0
        player.max_hp = 160.0
        player.mana = 100.0
        self.events.append({"type": "player_transformed", "player_id": player.id, "x": player.x, "y": player.y})

    def force_transform(self, player_id: str) -> None:
        """Bascule un joueur entre humain et monstre (pour tests/débug)."""
        player = self.players.get(player_id)
        if not player:
            return
        if not player.is_monster:
            self._transform_player_to_monster(player)
        else:
            player.is_monster = False
            player.hp = 100.0
            player.max_hp = 100.0
            player.mana = 100.0
            self.events.append({"type": "player_untransformed", "player_id": player.id})

    def spawn_bot_ally(self) -> None:
        """Génère un allié bot dans la salle de départ pour tests."""
        bot_id = f"bot_{random.randint(1000, 9999)}"
        self.add_player(bot_id, f"Bot Ally {bot_id[-4:]}", "elf_m")

    def step(self, dt: float = 1.0 / 30.0) -> None:
        """Tick autoritaire serveur à 30 Hz."""
        now = time.time()

        # 0. Score de survie en temps réel & apparition continue des monstres.
        # Tant qu'au moins un humain est en vie :
        #   - chaque humain accumule du temps de survie ;
        #   - chaque joueur transformé accumule du temps « monstre » (pénalité),
        #     puisque d'autres joueurs humains sont encore en vie.
        # score = survival_time - monster_active_time
        survivors_now = self._living_humans()
        if self.game_status == "RUNNING" and len(survivors_now) >= 1:
            for p in self.players.values():
                if p.is_monster:
                    p.monster_active_time += dt
                else:
                    p.survival_time += dt
                p.score = round(p.survival_time - p.monster_active_time, 1)
            self._update_monster_spawning(dt)

        # 1. Mise à jour des joueurs
        for player in self.players.values():
            # Régénération passive de mana pour les humains
            if not player.is_monster and player.mana < player.max_mana:
                player.mana = min(player.max_mana, player.mana + 5.0 * dt)

            # Décrémentation des cooldowns
            for k in list(player.spell_cooldowns.keys()):
                if player.spell_cooldowns[k] > 0:
                    player.spell_cooldowns[k] = max(0.0, player.spell_cooldowns[k] - dt)

            # Déplacement vers la cible du clic droit + couplage lampe torche
            self._update_player_movement(player, dt, now)

            # Bruit sonore et micro
            speed = math.hypot(player.vx, player.vy)
            if speed > MOVING_SPEED_THRESHOLD:
                base_noise = 18.0 if player.sneak else 65.0
            else:
                base_noise = 0.0

            if player.noise_event_timer > 0:
                player.noise_event_timer -= dt
                if player.noise_event_timer <= 0:
                    player.noise_radius = base_noise
            else:
                player.noise_radius = base_noise

            player.noise_radius += player.mic_rms * 240.0

        # 2. Mise à jour des projectiles
        alive_projectiles: list[ProjectileState] = []
        for proj in self.projectiles:
            proj.life -= dt
            if proj.life <= 0:
                continue

            proj.x += proj.vx * dt
            proj.y += proj.vy * dt

            # Collision avec mur
            ptx = int(proj.x // TILE_SIZE)
            pty = int(proj.y // TILE_SIZE)
            if is_cell_blocking(self.grid, ptx, pty):
                self.events.append({"type": "explosion", "x": proj.x, "y": proj.y, "kind": proj.kind})
                continue

            hit = False
            # Collision avec monstres IA
            for m in self.monsters:
                if m.hp > 0 and math.hypot(m.x - proj.x, m.y - proj.y) <= (m.speed * 0.1 + 8.5):
                    m.hp -= proj.damage
                    hit = True
                    self.events.append({
                        "type": "hit",
                        "attacker_id": proj.owner_id,
                        "target_id": m.id,
                        "damage": proj.damage,
                        "x": m.x,
                        "y": m.y,
                    })
                    if m.hp <= 0:
                        self.monsters_killed += 1
                        self.events.append({
                            "type": "monster_killed",
                            "monster_id": m.id,
                            "killer_id": proj.owner_id,
                            "total_killed": self.monsters_killed,
                            "x": m.x,
                            "y": m.y,
                        })
                    break

            if hit:
                self.events.append({"type": "explosion", "x": proj.x, "y": proj.y, "kind": proj.kind})
                continue

            # Collision avec monstre joueur (étourdissement)
            for p in self.players.values():
                if p.id != proj.owner_id and p.is_monster and p.hp > 0:
                    if math.hypot(p.x - proj.x, p.y - proj.y) <= 9.0:
                        p.stun_until = now + 2.0
                        p.clear_move_target()
                        p.hp -= proj.damage * 0.5
                        hit = True
                        self.events.append({
                            "type": "monster_stunned",
                            "target_id": p.id,
                            "stun_duration": 2.0,
                            "x": p.x,
                            "y": p.y,
                        })
                        if p.hp <= 0:
                            # Monstre Immortel : pas de mort définitive, réapparition éloignée
                            self._respawn_player_monster(p)
                        break

            if hit:
                self.events.append({"type": "explosion", "x": proj.x, "y": proj.y, "kind": proj.kind})
                continue

            alive_projectiles.append(proj)
        self.projectiles = alive_projectiles

        # Les monstres IA éliminés sont retirés du monde (le plafond ne compte que les vivants)
        self.monsters = [m for m in self.monsters if m.hp > 0]

        # 3. Machine à états de l'IA (« Chasseur Honnête »)
        self._update_monsters_ai(dt)

        # 4. Fin de partie : uniquement quand tous les humains présents sont devenus monstres.
        survivors = self._living_humans()
        if self.game_status == "RUNNING" and self.players and len(survivors) == 0:
            self.game_status = "GAME_OVER"
            ranking = sorted(self.players.values(), key=lambda p: p.score, reverse=True)
            self.final_ranking = [
                {
                    "id": p.id,
                    "name": p.name,
                    "score": round(p.score, 1),
                    "survival_time": round(p.survival_time, 1),
                    "monster_active_time": round(p.monster_active_time, 1),
                }
                for p in ranking
            ]
            self.events.append({
                "type": "game_over",
                "monsters_killed": self.monsters_killed,
                "ranking": self.final_ranking,
            })

    def _update_monsters_ai(self, dt: float) -> None:
        """IA Chasseur Honnête sans triche pour chaque monstre."""
        survivors = [p for p in self.players.values() if not p.is_monster and p.hp > 0]

        for m in self.monsters:
            if m.hp <= 0:
                continue

            m.repath_cd -= dt
            m.attack_cd -= dt

            # 1. Perception honnête : Vue et Ouïe
            detected_player: PlayerState | None = None
            min_dist = float("inf")

            for p in survivors:
                dist = math.hypot(p.x - m.x, p.y - m.y)
                has_los, wall_count = has_line_of_sight(self.grid, m.x, m.y, p.x, p.y)

                # Vue : cône lampe torche ou portée normale
                angle_to_m = math.atan2(m.y - p.y, m.x - p.x)
                diff = abs((angle_to_m - p.aim_angle + math.pi) % (2 * math.pi) - math.pi)
                in_torch = diff <= math.radians(40)
                view_range = 230.0 if in_torch else 165.0

                sees = (dist <= view_range) and has_los
                effective_noise = p.noise_radius * (0.55 ** wall_count)
                hears = dist <= effective_noise

                if (sees or hears) and dist < min_dist:
                    min_dist = dist
                    detected_player = p

            # 2. Transition d'état
            if detected_player:
                m.last_known_pos = (detected_player.x, detected_player.y)
                m.target_player_id = detected_player.id
                m.state = "CHASE"
                m.speed = 76.0

            # 3. Comportement par état
            if m.state == "CHASE":
                if m.last_known_pos:
                    mtx = int(m.x // TILE_SIZE)
                    mty = int(m.y // TILE_SIZE)
                    ptx = int(m.last_known_pos[0] // TILE_SIZE)
                    pty = int(m.last_known_pos[1] // TILE_SIZE)

                    if m.repath_cd <= 0:
                        m.path = astar_grid_path(self.grid, (mtx, mty), (ptx, pty))
                        m.repath_cd = 0.35

                    # Suivi du chemin A*
                    dist_to_last = math.hypot(m.last_known_pos[0] - m.x, m.last_known_pos[1] - m.y)
                    if dist_to_last <= 12.0 and not detected_player:
                        # Arrivé au dernier point connu sans revoir la cible -> SEARCH
                        m.state = "SEARCH"
                        m.speed = 50.0
                        m.search_timer = 4.5
                        m.search_targets = self._pick_search_targets(mtx, mty)
                    else:
                        self._follow_path(m, dt)

            elif m.state == "SEARCH":
                m.search_timer -= dt
                if m.search_timer <= 0:
                    m.state = "PATROL"
                    m.speed = 42.0
                    m.path = []
                    m.target_player_id = None
                else:
                    if not m.path and m.search_targets:
                        target_cell = m.search_targets.pop(0)
                        mtx = int(m.x // TILE_SIZE)
                        mty = int(m.y // TILE_SIZE)
                        m.path = astar_grid_path(self.grid, (mtx, mty), target_cell)
                    self._follow_path(m, dt)

            elif m.state == "PATROL":
                if not m.path:
                    m.patrol_idle_timer -= dt
                    if m.patrol_idle_timer <= 0:
                        rooms = self.dungeon.get("rooms", [])
                        if rooms:
                            chosen = random.choice(rooms)
                            cx = chosen.get("cx", 10)
                            cy = chosen.get("cy", 10)
                            mtx = int(m.x // TILE_SIZE)
                            mty = int(m.y // TILE_SIZE)
                            m.path = astar_grid_path(self.grid, (mtx, mty), (cx, cy))
                        m.patrol_idle_timer = 2.0
                self._follow_path(m, dt)

            # 4. Attaque au corps à corps
            if m.attack_cd <= 0:
                for p in survivors:
                    if math.hypot(p.x - m.x, p.y - m.y) <= 15.0:
                        p.hp -= 25.0
                        m.attack_cd = 1.0
                        self.events.append({
                            "type": "hit",
                            "attacker_id": m.id,
                            "target_id": p.id,
                            "damage": 25.0,
                            "x": p.x,
                            "y": p.y,
                        })
                        if p.hp <= 0:
                            self._transform_player_to_monster(p)
                        break

    def _pick_search_targets(self, cx: int, cy: int) -> list[tuple[int, int]]:
        """Trouve 2 cases praticables aux alentours pour fouiller."""
        cands: list[tuple[int, int]] = []
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                tx = cx + dx
                ty = cy + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if not is_cell_blocking(self.grid, tx, ty):
                        cands.append((tx, ty))
        if cands:
            return random.sample(cands, min(2, len(cands)))
        return []

    def _follow_path(self, m: MonsterState, dt: float) -> None:
        """Déplace le monstre vers la prochaine tuile de son chemin A*."""
        if not m.path:
            m.vx = 0.0
            m.vy = 0.0
            m.anim = "idle"
            return

        next_tx, next_ty = m.path[0]
        tgt_x = next_tx * 16.0 + 8.0
        tgt_y = next_ty * 16.0 + 8.0

        dx = tgt_x - m.x
        dy = tgt_y - m.y
        dist = math.hypot(dx, dy)

        if dist < 6.0:
            m.path.pop(0)
            if not m.path:
                m.vx = 0.0
                m.vy = 0.0
                return
            next_tx, next_ty = m.path[0]
            tgt_x = next_tx * 16.0 + 8.0
            tgt_y = next_ty * 16.0 + 8.0
            dx = tgt_x - m.x
            dy = tgt_y - m.y
            dist = math.hypot(dx, dy)

        if dist > 0.001:
            m.vx = (dx / dist) * m.speed
            m.vy = (dy / dist) * m.speed
            m.aim_angle = math.atan2(dy, dx)
            m.facing_left = m.vx < 0
            m.anim = "run"
        else:
            m.vx = 0.0
            m.vy = 0.0
            m.anim = "idle"

        new_x, new_y, collided = move_entity_with_collision(
            self.grid, m.x, m.y, m.vx, m.vy, dt, r=5.5
        )
        m.x = new_x
        m.y = new_y
        if collided:
            m.repath_cd = 0.0

    def get_snapshot(self) -> dict[str, Any]:
        """Retourne l'état complet actuel pour diffusion WebSocket et vide les événements."""
        players_dict = {p.id: p.to_dict() for p in self.players.values()}
        snapshot = {
            "room_id": self.room_id,
            "status": self.game_status,
            "game_status": self.game_status,
            "players": players_dict,
            "players_list": list(players_dict.values()),
            "monsters": [m.to_dict() for m in self.monsters],
            "projectiles": [proj.to_dict() for proj in self.projectiles],
            "monsters_killed": self.monsters_killed,
            "next_monster_spawn_in": round(max(0.0, self.monster_spawn_timer), 1),
            "final_ranking": self.final_ranking,
            "fountains": self.fountains,
            "tile_updates": list(self.pending_tile_updates),
            "pending_tile_updates": list(self.pending_tile_updates),
            "events": list(self.events),
        }
        self.pending_tile_updates.clear()
        self.events.clear()
        return snapshot
