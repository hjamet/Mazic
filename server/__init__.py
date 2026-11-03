"""
server package for Mazic Web & Multiplayer Engine.
"""

from server.maze_generator import (
    DungeonGenerator,
    VOID,
    FLOOR,
    WALL,
    DOOR_CLOSED,
    DOOR_OPEN,
)

__all__ = [
    "DungeonGenerator",
    "VOID",
    "FLOOR",
    "WALL",
    "DOOR_CLOSED",
    "DOOR_OPEN",
]
