[![libera manifesto](https://img.shields.io/badge/libera-manifesto-lightgrey.svg)](https://liberamanifesto.com)
[![Tests](https://img.shields.io/badge/pytest-13%20passed-brightgreen.svg)]()
[![Python](https://img.shields.io/badge/python-3.9%20|%203.11%20|%203.13-blue.svg)]()

# Mazic

**Mazic** is a fast-paced 2D roguelike labyrinth game in which you play a wizard trapped in an ever-shifting, dynamically generated maze haunted by lethal guardians and rival spellcasters. Unlock arcane abilities, reshape walls, survive against bloodthirsty monsters... or become one yourself!

---

## 🔮 Core Gameplay Mechanics

### 1. The 4 Mazic Spells (`SpellBook`)
Wizards manage a dynamic **Mana pool** (100 MP baseline with continuous regeneration) and command 4 distinct arcane powers:
- **`[1] Orbe Pyrique` (Fireball, 10 MP)**: Directional projectile delivering instant arcane damage to monsters and rivals.
- **`[2] Brise-Mur Runique` (Wall Alter, 25 MP)**: Alter labyrinth topography! Destroys an adjacent internal wall into walkable floor, or conjures a runic wall on empty ground.
- **`[3] Œil d'Arcane` (Arcane Sight, 20 MP)**: Ethereal vision bypassing stone walls and extending perception radius for 6 seconds.
- **`[4] Pas Astral` (Blink, 30 MP)**: Instantaneous short-range teleportation to any visible, walkable tile within range (rejects solid walls).

### 2. The Signature Mechanic: Immortal Monster Transformation
> *"Quand on est tué par un monstre, on ne meurt pas passivement : on se transforme en Monstre Immortel, et notre objectif devient de traquer les autres joueurs !"* — Henri Jamet

When the player's health drops to 0 HP:
- Immediate resurrection as an **Immortal Monster** (`is_immortal_monster = True`).
- Health fully restored to maximum.
- **1.35x speed boost** and enhanced darkvision.
- Switch to the monster faction to hunt down remaining wizards in the maze.

### 3. Fog of War & Spatial Memory
- **2D Raycasting (Bresenham)**: Line of sight realistically blocked by stone walls.
- **Tile Visibility States**: `VISIBLE` (currently lit by arcane torch), `EXPLORED` (remembered in spatial memory), `UNEXPLORED` (pitch-black darkness).
- **Heads-Up Display & Minimap**: Real-time HUD showing Health, Mana, spell slots, player status (Mage vs Immortal Monster), and an interactive minimap of explored rooms.

---

## 🏗️ Architecture

```
mazic/
├── src/
│   ├── Mazic.py                     # Main Pygame game loop & event dispatcher
│   ├── Camera.py                    # Smooth 2D scrolling camera & viewport
│   ├── EntityManager.py             # Entity-Component manager & collision system
│   ├── Entities/
│   │   ├── Character.py             # Wizard character (SpellBook + Immortal Monster logic)
│   │   ├── Monster.py               # Labyrinth guardian demons & transformation logic
│   │   ├── Projectile.py            # Arcane projectiles
│   │   └── Maze/                    # Floor & Wall tiles
│   ├── EntityPlugins/
│   │   ├── SpellBook.py             # Mana pool, regen, 4 Mazic spells & inventory
│   │   ├── Health.py                # Health management & health bar rendering
│   │   └── AbilityManager.py        # Cooldown & capability manager
│   ├── MazeGenerator/
│   │   ├── MazeManager.py           # Real-time procedural room expansion & dead-end sealing
│   │   ├── RoomSpawner.py           # Room template loader & entrance matching
│   │   └── FogOfWar.py              # Bresenham FOV raycasting & explored tile memory
│   ├── UI/
│   │   └── HUD.py                   # Health/Mana gauges, spell bar & real-time minimap
│   └── Audio/
│       └── SoundManager.py          # Procedural PCM synthesizer (headless compatible)
├── web/
│   └── index.html                   # Standalone Web HTML5/Canvas 1-click playable edition
├── assets/
│   ├── rooms/                       # Procedural JSON room templates
│   └── frames/                      # 16px pixel art sprites & animations
└── tests/
    └── test_mazic.py                # 13 automated Pytest integration & unit tests
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+ (tested on Python 3.11 and 3.13)
- Pygame `>= 2.5.2`, NumPy `>= 1.26.0`

### Installation

```sh
# Clone repository
git clone https://github.com/hjamet/Mazic.git
cd Mazic

# Install dependencies with pip
pip install pygame numpy pandas pytest

# Or with Poetry
poetry install
```

### Running the Python / Pygame Engine
```sh
python src/main.py
```

**Controls**:
- `Z Q S D` / `W A S D` / Arrow Keys: Move wizard
- `Mouse Left Click`: Auto-attack / Cast targeted spell
- `1` / `2` / `3` / `4`: Cast Fireball, Wall Alter, Arcane Sight, or Blink

---

## 🧪 Automated Test Suite

Mazic includes **13 automated tests** covering geometric room generation, alignment, collision handling, line of sight, spellcasting mechanics, and immortal monster transformation:

```sh
python -m pytest -v
```

```
tests/test_mazic.py::test_room_spawner_no_coordinate_accumulation PASSED
tests/test_mazic.py::test_all_room_templates_valid_and_have_entrances PASSED
tests/test_mazic.py::test_dynamic_maze_generation_alignment PASSED
tests/test_mazic.py::test_dead_end_sealing_on_blocked_entrance PASSED
tests/test_mazic.py::test_issue21_floor_has_no_hitbox PASSED
tests/test_mazic.py::test_fog_of_war_raycasting_and_wall_occlusion PASSED
tests/test_mazic.py::test_fog_of_war_memory_explored_tiles PASSED
tests/test_mazic.py::test_spellbook_mana_consumption_and_regen PASSED
tests/test_mazic.py::test_spellbook_wall_alter_mechanic PASSED
tests/test_mazic.py::test_spellbook_arcane_sight_penetration PASSED
tests/test_mazic.py::test_spellbook_blink_teleportation PASSED
tests/test_mazic.py::test_immortal_monster_transformation_on_death PASSED
tests/test_mazic.py::test_hud_minimap_generation_and_sound_manager_headless PASSED
```

---

## 📜 License
Apache License 2.0 / MIT. Created by Henri Jamet.