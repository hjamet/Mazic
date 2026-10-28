import pygame
from typing import Optional, Tuple, Any


class HUD:
    """Renders the Mazic heads-up display: HP bar, Mana bar, Spell slots,

    immortal monster status, and an interactive real-time minimap.
    """

    def __init__(self, font_name: Optional[str] = None, font_size: int = 14) -> None:
        self.font_size = font_size
        if pygame.font.get_init():
            self.font = pygame.font.Font(font_name, font_size)
            self.title_font = pygame.font.Font(font_name, font_size + 4)
        else:
            pygame.font.init()
            self.font = pygame.font.Font(font_name, font_size)
            self.title_font = pygame.font.Font(font_name, font_size + 4)

    def generate_minimap_surface(
        self,
        fog_of_war: Any,
        maze_manager: Any,
        player_pos: Tuple[float, float],
        map_size: Tuple[int, int] = (160, 160),
    ) -> pygame.Surface:
        """Generates a real-time minimap surface depicting explored tiles and player position.

        Args:
            fog_of_war: FogOfWar instance with explored_tiles and visible_tiles.
            maze_manager: MazeManager instance or None.
            player_pos: (px, py) world coordinates.
            map_size: (width, height) of the minimap in pixels.

        Returns:
            pygame.Surface: Rendered minimap surface.
        """
        minimap = pygame.Surface(map_size, pygame.SRCALPHA)
        minimap.fill((15, 18, 25, 210))  # Dark transparent background
        pygame.draw.rect(minimap, (70, 90, 130), (0, 0, map_size[0], map_size[1]), 2)

        cx, cy = map_size[0] // 2, map_size[1] // 2
        px, py = player_pos
        player_gx = px / 16.0
        player_gy = py / 16.0
        scale = 3  # 3 pixels per tile

        # Draw explored and visible tiles
        if fog_of_war is not None:
            explored = getattr(fog_of_war, "explored_tiles", set())
            visible = getattr(fog_of_war, "visible_tiles", set())

            # Draw explored tiles (dim blue/gray)
            for gx, gy in explored:
                mx = int(cx + (gx - player_gx) * scale)
                my = int(cy + (gy - player_gy) * scale)
                if 2 <= mx < map_size[0] - 2 and 2 <= my < map_size[1] - 2:
                    minimap.fill((45, 60, 85), (mx, my, scale, scale))

            # Draw currently visible tiles (bright arcane cyan)
            for gx, gy in visible:
                mx = int(cx + (gx - player_gx) * scale)
                my = int(cy + (gy - player_gy) * scale)
                if 2 <= mx < map_size[0] - 2 and 2 <= my < map_size[1] - 2:
                    minimap.fill((70, 140, 200), (mx, my, scale, scale))

        # Draw player marker at center
        pygame.draw.circle(minimap, (0, 255, 255), (cx, cy), 3)

        return minimap

    def render(
        self,
        screen: pygame.Surface,
        character: Any,
        fog_of_war: Any = None,
        maze_manager: Any = None,
    ) -> None:
        """Renders the full HUD onto the active game screen.

        Args:
            screen (pygame.Surface): The game screen surface.
            character: Character instance.
            fog_of_war: Optional FogOfWar instance.
            maze_manager: Optional MazeManager instance.
        """
        sw, sh = screen.get_size()

        # 1. Health Bar (Red/Green)
        max_hp = getattr(character, "max_hp", 100)
        hp = getattr(character, "hp", max_hp)
        hp_ratio = max(0.0, min(1.0, hp / max_hp)) if max_hp > 0 else 0.0

        bar_width = 200
        bar_height = 18
        hp_x, hp_y = 20, 20

        # Background
        pygame.draw.rect(screen, (30, 30, 30), (hp_x - 2, hp_y - 2, bar_width + 4, bar_height + 4))
        pygame.draw.rect(screen, (100, 20, 20), (hp_x, hp_y, bar_width, bar_height))
        pygame.draw.rect(screen, (40, 200, 40), (hp_x, hp_y, int(bar_width * hp_ratio), bar_height))
        hp_text = self.font.render(f"PV: {int(hp)}/{int(max_hp)}", True, (255, 255, 255))
        screen.blit(hp_text, (hp_x + 5, hp_y + 2))

        # 2. Mana Bar (Blue/Cyan)
        spellbook = getattr(character, "spellbook", None)
        mana = getattr(spellbook, "mana", 100.0) if spellbook else 100.0
        max_mana = getattr(spellbook, "max_mana", 100.0) if spellbook else 100.0
        mana_ratio = max(0.0, min(1.0, mana / max_mana)) if max_mana > 0 else 0.0

        mana_x, mana_y = 20, 44
        pygame.draw.rect(screen, (30, 30, 30), (mana_x - 2, mana_y - 2, bar_width + 4, bar_height + 4))
        pygame.draw.rect(screen, (20, 30, 80), (mana_x, mana_y, bar_width, bar_height))
        pygame.draw.rect(screen, (30, 140, 255), (mana_x, mana_y, int(bar_width * mana_ratio), bar_height))
        mana_text = self.font.render(f"Mana: {int(mana)}/{int(max_mana)}", True, (255, 255, 255))
        screen.blit(mana_text, (mana_x + 5, mana_y + 2))

        # 3. Status indicator: Mage vs Monstre Immortel
        is_monster = getattr(character, "is_immortal_monster", False)
        status_str = "MONSTRE IMMORTEL" if is_monster else "MAGE"
        status_color = (255, 50, 50) if is_monster else (100, 220, 255)
        status_surf = self.title_font.render(f"Statut: {status_str}", True, status_color)
        screen.blit(status_surf, (hp_x, 70))

        # 4. Spells bar (Bottom center)
        spells_info = [
            ("[1] Orbe Pyrique", "10 MP", (255, 120, 40)),
            ("[2] Brise-Mur Runique", "25 MP", (180, 140, 255)),
            ("[3] Oeil d'Arcane", "20 MP", (60, 220, 255)),
            ("[4] Pas Astral", "30 MP", (240, 220, 80)),
        ]
        slot_w, slot_h = 130, 42
        total_spells_w = len(spells_info) * (slot_w + 10) - 10
        start_x = (sw - total_spells_w) // 2
        spells_y = sh - 55

        for i, (name, cost, color) in enumerate(spells_info):
            sx = start_x + i * (slot_w + 10)
            pygame.draw.rect(screen, (20, 25, 35, 220), (sx, spells_y, slot_w, slot_h))
            pygame.draw.rect(screen, color, (sx, spells_y, slot_w, slot_h), 2)
            name_surf = self.font.render(name, True, color)
            cost_surf = self.font.render(cost, True, (200, 200, 200))
            screen.blit(name_surf, (sx + 5, spells_y + 4))
            screen.blit(cost_surf, (sx + 5, spells_y + 22))

        # 5. Minimap (Top Right)
        if fog_of_war is not None:
            minimap_surf = self.generate_minimap_surface(
                fog_of_war,
                maze_manager,
                (getattr(character, "x", 0), getattr(character, "y", 0)),
                (150, 150),
            )
            screen.blit(minimap_surf, (sw - 165, 15))
