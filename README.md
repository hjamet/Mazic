# Mazic

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![WebSockets](https://img.shields.io/badge/WebSockets-30Hz%20Authoritative-blue.svg)]()
[![0x72](https://img.shields.io/badge/Tileset-0x72__DungeonTilesetII-orange.svg)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](LICENSE)

**Mazic** est un jeu roguelike multijoueur 2D en ligne temps réel, 100 % jouable dans le navigateur sans installation. Incarnez un mage arcanique pris au piège dans un donjon labyrinthique généré procéduralement, harcelé par des monstres impitoyables et des rivaux. Collectez les cristaux d'arcane pour activer le portail d'évasion... ou devenez un monstre immortel traquant vos anciens compagnons !

---

## 🔮 Mécaniques de Jeu Clés

### 1. Multijoueur Autoritaire 30 Hz
- **Serveur maître** : Toute la physique AABB, le raycasting, l'IA et la résolution des sorts sont exécutés côté serveur à **30 ticks/seconde** (`server/game_engine.py`).
- **Clients synchronisés** : Les navigateurs reçoivent les snapshots d'état via WebSockets ultra-rapides et effectuent une interpolation douce des trajectoires.

### 2. Autotiler 2.5D Authentique `0x72_DungeonTilesetII`
- **Rendu en fausse perspective 2.5D** : Algorithme de bitmask 8-voisins générant faces frontales de mur (`wall_mid`), coins (`wall_left`, `wall_right`), bannières et décors de donjon (`assets/frames/`).
- **Superposition foreground (`z-index`)** : Les rebords supérieurs des murs (`wall_top_mid`) passent devant la tête des personnages au nord, et derrière les personnages au sud.

### 3. Les 4 Sortilèges Arcaniques (`SpellBook`)
- **`[1] Orbe Pyrique` (20 Mana)** : Projectile magique infligeant des dégâts aux monstres ou étourdissant les monstres joueurs.
- **`[2] Brise-Mur Runique` (30 Mana)** : Altère le donjon en temps réel ! Détruit un mur intérieur en sol praticable, ou érige une barricade magique pour stopper une poursuite (avec mise à jour immédiate de l'autotiling).
- **`[3] Œil d'Arcane` (25 Mana)** : Vision éthérée traversant les murs et perception élargie pendant 5 secondes.
- **`[4] Pas Astral` (35 Mana)** : Téléportation courte portée instantanée vers une case visible praticable.

### 4. Esprit de Ruche & Transformation en Monstre Immortel
> *"Quand on est tué par un monstre, on ne meurt pas passivement : on se transforme en Monstre Immortel, et notre objectif devient de traquer les autres joueurs !"* — Henri Jamet

- À 0 PV, le joueur humain renaît instantanément sous la forme d'un **Monstre Immortel** (`big_demon` / `chort`).
- PV augmentés à 160, vitesse accrue (+20 %), attaque de griffe sauvage au corps-à-corps (28 dégâts).
- Vision nocturne dans les ténèbres et **Voix Démoniaque** appliquée en direct sur le flux microphone !

### 5. IA « Chasseur Honnête » (Zéro Omniscience)
- **Perception réaliste** : Les monstres IA ne trichent pas. Ils détectent les joueurs par **vue directe** (raycasting DDA, cône de torche) et par **ouïe** (bruits de pas, sorts, microphone du joueur atténué par les murs).
- **Machine à états tactique** : `PATROL` (rondes) ➔ `CHASE` (poursuite vers la dernière position vue/entendue via le plus court chemin A*) ➔ `SEARCH` (inspection aux embranchements après perte de vue).

### 6. Voice Proximity & Relais Audio Basse Latence
- **Voix de proximité spatialisée** : Volume et panoramique stéréo calculés selon la distance et l'occlusion des murs.
- **Double canal** : Signalisation P2P WebRTC avec fallback automatique via relais WebSocket (`voice_frame`), garantissant une voix 100 % fonctionnelle à travers les tunnels et pare-feux.

---

## 🏗️ Architecture du Projet

```
mazic/
├── server/
│   ├── __init__.py
│   ├── maze_generator.py      # Donjon procédural (graphe de salles, couloirs larges, autotiler 2.5D)
│   ├── game_engine.py         # Moteur serveur autoritaire 30 Hz, collisions AABB, IA Chasseur Honnête A*
│   └── app.py                 # Serveur FastAPI, WebSockets /ws/{room_id}, relais WebRTC/Voice
├── web/
│   ├── index.html             # Interface et Canvas HTML5 plein écran
│   ├── game.js                # Moteur client (rendu 2.5D, autotiling dynamique, interpolation)
│   └── voice.js               # Audio de proximité, capture microphone, filtres voix démoniaque
├── assets/
│   └── frames/                # 368 sprites pixel art originaux 0x72_DungeonTilesetII
├── start_online.py            # Lanceur 1-clic avec tunnel public Cloudflare automatique
├── pyproject.toml             # Configuration du projet (FastAPI, Uvicorn, WebSockets, NumPy)
└── README.md
```

---

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.9+ (testé sur Python 3.11 et 3.12)
- Outil `uv` (recommandé) ou `pip`

### 1. Installation des dépendances

```sh
# Avec uv (ultra-rapide)
uv sync

# Ou avec pip standard
pip install fastapi "uvicorn[standard]" websockets numpy
```

### 2. Lancement en 1-clic (Serveur local + Tunnel public mondial)

```sh
python start_online.py
```

Le script démarre automatiquement :
1. Le serveur FastAPI autoritaire sur le port local `8090` (dual-stack `::` / `127.0.0.1`).
2. Le tunnel Cloudflare sans compte pour générer une URL publique `https://....trycloudflare.com`.
3. Affiche l'URL publique à partager avec vos amis !

Pour un test purement local :
```sh
python -m uvicorn server.app:app --host 127.0.0.1 --port 8090
```
Ouvrez ensuite [http://localhost:8090](http://localhost:8090) dans votre navigateur.

---

## 🎮 Contrôles en Jeu

| Action | Touche / Contrôle |
|---|---|
| **Déplacement** | `Z Q S D` / `W A S D` / Flèches directionnelles |
| **Marche Silencieuse (Sneak)** | Maintenir `Shift` (réduit le bruit pour échapper aux monstres) |
| **Visée & Torche** | Souris (oriente le faisceau lumineux et les sorts) |
| **Attaque de base** | Clic gauche |
| **Sorts 1 / 2 / 3 / 4** | Touches `1`, `2`, `3`, `4` (ou barre de sorts en bas d'écran) |
| **Interagir / Portes / Fontaines** | Touche `E` |
| **Mode Test Monstre Immortel** | Bouton `Transformer en Monstre` (test instantané de l'Esprit de Ruche) |
| **Nouvelle Partie** | Bouton `Recommencer la partie` (regénère un donjon pour tous les joueurs) |

---

## 📜 Licence
Apache License 2.0. Développé par Henri Jamet.