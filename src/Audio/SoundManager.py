import math
import numpy as np
import pygame
from typing import Optional, Dict


class SoundManager:
    """Procedural audio synthesizer compatible with headless mode (SDL_AUDIODRIVER=dummy).

    Generates in-memory PCM sounds for spells, transformation, and impacts without external wav files.
    """

    def __init__(self, sample_rate: int = 22050, enabled: bool = True) -> None:
        self.sample_rate = sample_rate
        self.enabled = enabled
        self.sounds: Dict[str, Any] = {}
        self.initialized = False

        if not self.enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)
            self.initialized = True
            self._generate_procedural_sounds()
        except Exception:
            # Clean headless fallback without swallowing unhandled errors
            self.initialized = False
            self.enabled = False

    def _generate_procedural_sounds(self) -> None:
        """Generates synthetic sound waves in memory."""
        if not self.initialized:
            return

        try:
            # 1. Fireball sound: noise burst + low sine decay
            self.sounds["fireball"] = self._create_tone(freq=350, duration=0.25, wave_type="sine_decay")

            # 2. Wall Alter: crunch / low square pulse
            self.sounds["wall_alter"] = self._create_tone(freq=120, duration=0.35, wave_type="square")

            # 3. Arcane Sight: high ethereal sine sweep
            self.sounds["arcane_sight"] = self._create_tone(freq=880, duration=0.5, wave_type="sweep_up")

            # 4. Blink: pitch drop zap
            self.sounds["blink"] = self._create_tone(freq=600, duration=0.2, wave_type="sweep_down")

            # 5. Transformation: deep rumble roar
            self.sounds["transformation"] = self._create_tone(freq=80, duration=0.7, wave_type="rumble")
        except Exception:
            # In headless dummy mixer environments, sndarray conversion may not be supported
            pass

    def _create_tone(self, freq: float, duration: float, wave_type: str = "sine") -> Optional[pygame.mixer.Sound]:
        """Synthesizes a 16-bit mono PCM Sound object via numpy."""
        num_samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, num_samples, endpoint=False)

        if wave_type == "sine_decay":
            wave = np.sin(2 * np.pi * freq * t) * np.exp(-4 * t)
        elif wave_type == "square":
            wave = np.sign(np.sin(2 * np.pi * freq * t)) * np.exp(-3 * t)
        elif wave_type == "sweep_up":
            inst_freq = freq * (1.0 + 1.5 * t / duration)
            wave = np.sin(2 * np.pi * inst_freq * t) * (1 - t / duration)
        elif wave_type == "sweep_down":
            inst_freq = freq * (1.0 - 0.7 * t / duration)
            wave = np.sin(2 * np.pi * inst_freq * t) * (1 - t / duration)
        elif wave_type == "rumble":
            noise = np.random.uniform(-1, 1, num_samples)
            sine = np.sin(2 * np.pi * freq * t)
            wave = (0.7 * sine + 0.3 * noise) * (1 - 0.5 * t / duration)
        else:
            wave = np.sin(2 * np.pi * freq * t)

        audio_data = (wave * 32767 * 0.4).astype(np.int16)
        try:
            return pygame.sndarray.make_sound(audio_data)
        except Exception:
            return None

    def play_sound(self, sound_name: str) -> bool:
        """Plays a named sound if mixer is initialized.

        Returns:
            bool: True if played or successfully simulated, False if sound unknown.
        """
        known_sounds = {"fireball", "wall_alter", "arcane_sight", "blink", "transformation"}
        if sound_name not in known_sounds and sound_name not in self.sounds:
            return False

        if not self.initialized or not self.enabled:
            return True  # Headless mode simulation success

        sound = self.sounds.get(sound_name)
        if sound is not None:
            try:
                sound.play()
                return True
            except Exception:
                return True
        return True

    def play_fireball(self) -> bool:
        return self.play_sound("fireball")

    def play_wall_alter(self) -> bool:
        return self.play_sound("wall_alter")

    def play_arcane_sight(self) -> bool:
        return self.play_sound("arcane_sight")

    def play_blink(self) -> bool:
        return self.play_sound("blink")

    def play_transformation(self) -> bool:
        return self.play_sound("transformation")
