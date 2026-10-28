import math
import pygame
from typing import Optional, List, Any
from EntityManager import Entity, AnimatedEntity, Event
from EntityPlugins.Health import Health


def transform_into_immortal_monster(character_or_state: Any) -> bool:
    """Transforms a fallen Mage into an Immortal Monster upon reaching <= 0 HP.

    In accordance with Henri Jamet's voicenote signature design:
    - Sets is_immortal_monster = True
    - Restores HP to max_hp (or increased baseline)
    - Grants 1.35x speed boost
    - Activates enhanced dark/arcane sight
    - Clears death status
    """
    if hasattr(character_or_state, "is_immortal_monster"):
        character_or_state.is_immortal_monster = True
    elif isinstance(character_or_state, dict):
        character_or_state["is_immortal_monster"] = True

    # Restore HP and revive
    if hasattr(character_or_state, "hp") and hasattr(character_or_state, "max_hp"):
        character_or_state.hp = character_or_state.max_hp
        character_or_state._is_dead = False
    elif isinstance(character_or_state, dict):
        character_or_state["hp"] = character_or_state.get("max_hp", 100)
        character_or_state["is_dead"] = False

    # Speed multiplier 1.35x
    if hasattr(character_or_state, "speed"):
        character_or_state.speed = round(character_or_state.speed * 1.35, 2)
    elif isinstance(character_or_state, dict) and "speed" in character_or_state:
        character_or_state["speed"] = round(character_or_state["speed"] * 1.35, 2)

    # Night vision / extended vision
    if hasattr(character_or_state, "has_darkvision"):
        character_or_state.has_darkvision = True
    elif isinstance(character_or_state, dict):
        character_or_state["has_darkvision"] = True

    return True


class Monster(Entity, AnimatedEntity, Health):
    """A labyrinth guardian monster that stalks and attacks wizards."""

    assets_needed = {
        "idle": [
            "big_demon_idle_anim_f0",
            "big_demon_idle_anim_f1",
            "big_demon_idle_anim_f2",
            "big_demon_idle_anim_f3",
        ],
        "run": [
            "big_demon_run_anim_f0",
            "big_demon_run_anim_f1",
            "big_demon_run_anim_f2",
            "big_demon_run_anim_f3",
        ],
    }

    animation_speed = {
        "idle": 0.08,
        "run": 0.15,
    }

    def __init__(
        self,
        name: str = "Guardian Demon",
        x: int = 0,
        y: int = 0,
        team: int = 2,
        max_hp: int = 80,
        speed: float = 1.5,
        damage_amount: int = 15,
    ) -> None:
        Entity.__init__(self)
        AnimatedEntity.__init__(
            self,
            camera_lvl=3,
            has_hitbox=True,
            has_mask=True,
            is_tangible=True,
            hitbox_height_ratio=0.6,
        )
        Health.__init__(self, max_hp=max_hp, is_main_character_health=False)

        self.name = name
        self.x = x
        self.y = y
        self.team = team
        self.speed = speed
        self.damage_amount = damage_amount
        self.attack_cooldown_ms = 1000
        self.last_attack_time = 0

    def update(self, event_list: list) -> list:
        new_events = []

        # Process damage events
        for event in event_list:
            if event.type == "damage" and "damage" in event.data:
                self.damage(event.data["damage"])
                if self.hp <= 0:
                    if self.entity_manager is not None:
                        self.entity_manager.remove(self)
                    return []

        # Find closest hostile character if entity_manager is available
        if self.entity_manager is not None and hasattr(self.entity_manager, "entities"):
            target = None
            min_dist = float("inf")
            for ent in self.entity_manager.entities:
                if ent != self and hasattr(ent, "hp") and getattr(ent, "team", None) != self.team:
                    dist = math.hypot(ent.x - self.x, ent.y - self.y)
                    if dist < min_dist:
                        min_dist = dist
                        target = ent

            if target is not None:
                if min_dist > 18:
                    dx = target.x - self.x
                    dy = target.y - self.y
                    norm = math.hypot(dx, dy)
                    if norm > 0:
                        self.x += (dx / norm) * self.speed
                        self.y += (dy / norm) * self.speed
                        self.set_animation("run", reverse=(dx < 0))
                else:
                    self.set_animation("idle")
                    current_time = pygame.time.get_ticks()
                    if current_time - self.last_attack_time >= self.attack_cooldown_ms:
                        self.last_attack_time = current_time
                        new_events.append(
                            Event(
                                targets_id=[target.id],
                                type="damage",
                                data={"damage": self.damage_amount},
                            )
                        )
            else:
                self.set_animation("idle")

        return new_events
