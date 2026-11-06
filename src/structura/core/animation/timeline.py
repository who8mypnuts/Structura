"""The timeline model (docs/16 §2.1): tracks of keyframes evaluated per frame. Qt-free and immutable.

A track's target is a string: 'param:NAME' (a #define slider or v2 #param), 'camera:eye.x' … 'camera:target.z',
'camera:fov', or 'seed' (stepped). Between keys a track is constant (hold), linear, or smooth (cubic
ease-in/out); the interpolation belongs to the key on the left. Outside its keys a track holds the end values.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

CAMERA_FIELDS = ("eye.x", "eye.y", "eye.z", "target.x", "target.y", "target.z", "fov")


class Interp(StrEnum):
    CONSTANT = "constant"
    LINEAR = "linear"
    SMOOTH = "smooth"


@dataclass(frozen=True)
class Key:
    frame: int
    value: float
    interp: Interp = Interp.SMOOTH


@dataclass(frozen=True)
class Track:
    target: str
    keys: tuple[Key, ...] = ()  # sorted by frame, one key per frame

    def value(self, frame: float) -> float | None:
        if not self.keys:
            return None
        frames = [k.frame for k in self.keys]
        i = bisect_right(frames, frame) - 1
        if i < 0:
            return self.keys[0].value
        if i >= len(self.keys) - 1:
            return self.keys[-1].value
        left, right = self.keys[i], self.keys[i + 1]
        t = (frame - left.frame) / (right.frame - left.frame)
        if left.interp is Interp.CONSTANT or self.target == "seed":
            return left.value
        if left.interp is Interp.SMOOTH:
            t = t * t * (3.0 - 2.0 * t)
        return left.value + (right.value - left.value) * t

    def with_key(self, key: Key) -> Track:
        keys = {k.frame: k for k in self.keys} | {key.frame: key}
        return replace(self, keys=tuple(keys[f] for f in sorted(keys)))

    def without_key(self, frame: int) -> Track:
        return replace(self, keys=tuple(k for k in self.keys if k.frame != frame))


@dataclass(frozen=True)
class Timeline:
    fps: float = 24.0
    start: int = 0
    end: int = 120
    tracks: tuple[Track, ...] = ()

    def track(self, target: str) -> Track | None:
        return next((t for t in self.tracks if t.target == target), None)

    def value(self, target: str, frame: float) -> float | None:
        track = self.track(target)
        return None if track is None else track.value(frame)

    def set_key(self, target: str, frame: int, value: float, interp: Interp = Interp.SMOOTH) -> Timeline:
        track = (self.track(target) or Track(target)).with_key(Key(frame, value, interp))
        return self._with_track(track)

    def set_interp(self, target: str, frame: int, interp: Interp) -> Timeline:
        track = self.track(target)
        key = next((k for k in track.keys if k.frame == frame), None) if track else None
        return self if key is None else self.set_key(target, frame, key.value, interp)

    def has_key(self, target: str, frame: int) -> bool:
        track = self.track(target)
        return track is not None and any(k.frame == frame for k in track.keys)

    def remove_key(self, target: str, frame: int) -> Timeline:
        track = self.track(target)
        if track is None:
            return self
        track = track.without_key(frame)
        return self._with_track(track) if track.keys else replace(self, tracks=self._others(target))

    def _others(self, target: str) -> tuple[Track, ...]:
        return tuple(t for t in self.tracks if t.target != target)

    def _with_track(self, track: Track) -> Timeline:
        tracks = [*self._others(track.target), track]
        return replace(self, tracks=tuple(sorted(tracks, key=lambda t: t.target)))

    def params_at(self, frame: float) -> dict[str, float]:
        """Values of every 'param:NAME' track."""
        out = {}
        for t in self.tracks:
            value = t.value(frame)
            if t.target.startswith("param:") and value is not None:
                out[t.target.removeprefix("param:")] = value
        return out

    def key_frames(self) -> list[int]:
        return sorted({k.frame for t in self.tracks for k in t.keys})

    def time(self, frame: float) -> float:
        return frame / self.fps


def to_dict(timeline: Timeline) -> dict[str, Any]:
    return {"fps": timeline.fps, "start": timeline.start, "end": timeline.end,
            "tracks": [{"target": t.target, "keys": [[k.frame, k.value, str(k.interp)] for k in t.keys]}
                       for t in timeline.tracks]}  # fmt: skip


def from_dict(data: Any) -> Timeline:
    """Tolerant: unknown interpolations become smooth, malformed keys are skipped."""
    if not isinstance(data, dict):
        return Timeline()
    timeline = Timeline(float(data.get("fps", 24.0)), int(data.get("start", 0)), int(data.get("end", 120)))
    for raw in data.get("tracks") or []:
        target = str(raw.get("target", "")) if isinstance(raw, dict) else ""
        for key in raw.get("keys") or [] if target else []:
            if isinstance(key, list) and len(key) >= 2:
                interp = Interp(key[2]) if len(key) > 2 and key[2] in set(Interp) else Interp.SMOOTH
                timeline = timeline.set_key(target, int(key[0]), float(key[1]), interp)
    return timeline
