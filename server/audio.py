"""Soft, generated WAV feedback; pygame supplies portable asynchronous playback."""
from __future__ import annotations

import io
import math
import os
import struct
import wave
from functools import lru_cache

RATE = 22050


@lru_cache(maxsize=8)
def make_sound(kind: str) -> bytes:
    frequencies = [523.25, 659.25, 783.99, 1046.5] if kind == 'document' else [523.25, 659.25, 783.99]
    chime = kind in {'section', 'document', 'preview'}
    duration = .95 if chime else .28
    output = bytearray()
    for index in range(int(RATE * duration)):
        time = index / RATE
        if chime:
            sample = 0.
            for i, frequency in enumerate(frequencies):
                local = time - i * .105
                if 0 <= local <= .62:
                    envelope = min(local / .025, 1) * math.exp(-local * 7)
                    sample += math.sin(math.tau * frequency * local) * envelope * .19
        else:
            frequency = 392 if kind == 'confident' else 329.63
            envelope = math.sin(math.pi * min(1, time / duration)) ** 2 * math.exp(-time * 6)
            sample = (math.sin(math.tau * frequency * time) * .2 + math.sin(math.tau * (190 * time - 120 * time * time)) * .08) * envelope
        output.extend(struct.pack('<h', round(max(-.95, min(.95, sample)) * 32767)))
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(output)
    return buffer.getvalue()


class DesktopAudio:
    def __init__(self):
        self.mixer = None
        self.error = ''

    def play(self, kind, volume=.35):
        if volume <= 0:
            return
        try:
            if self.mixer is None:
                os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
                from pygame import mixer
                mixer.init(frequency=RATE, size=-16, channels=1, buffer=512)
                self.mixer = mixer
            sound = self.mixer.Sound(file=io.BytesIO(make_sound(kind)))
            sound.set_volume(max(0, min(1, volume)))
            sound.play()
        except Exception as exc:
            # Audio output is optional on remote machines without speakers.
            self.error = f'Sound output is unavailable: {exc}'

    def stop(self):
        if self.mixer:
            self.mixer.stop()

    def close(self):
        if self.mixer:
            self.mixer.quit()
            self.mixer = None
