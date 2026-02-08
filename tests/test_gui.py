"""Tests for GUI helper modules (render + input) that don't require a display."""

import time

from PIL import Image

from d20roller.gui.input import ShakeDetector
from d20roller.gui.render import (
    generate_roll_animation_frames,
    render_die_frame,
    render_idle_die,
)


class TestRender:
    def test_idle_die_returns_rgba_image(self):
        img = render_idle_die()
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"
        assert img.size == (160, 160)

    def test_render_frame_custom_size(self):
        img = render_die_frame(10, size=64)
        assert img.size == (64, 64)

    def test_animation_frame_count(self):
        frames = generate_roll_animation_frames(15, max_face=20, num_frames=12)
        assert len(frames) == 12
        assert all(isinstance(f, Image.Image) for f in frames)

    def test_crit_and_fail_frames_render(self):
        crit = render_die_frame(20, is_crit=True)
        fail = render_die_frame(1, is_fail=True)
        assert crit.size == (160, 160)
        assert fail.size == (160, 160)


class TestShakeDetector:
    def test_not_pressed_returns_false(self):
        sd = ShakeDetector()
        assert not sd.feed(10, 10)

    def test_press_and_release(self):
        sd = ShakeDetector()
        sd.press()
        assert sd.is_pressed
        sd.release()
        assert not sd.is_pressed

    def test_calm_motion_no_trigger(self):
        sd = ShakeDetector(threshold=200)
        sd.press()
        # Very small movements
        for i in range(5):
            assert not sd.feed(i, i)

    def test_vigorous_shake_triggers(self):
        sd = ShakeDetector(threshold=100, cooldown_sec=0.0)
        sd.press()
        # Inject rapid oscillating samples within the time window
        now = time.monotonic()
        sd._samples = [(now + i * 0.01, (i % 2) * 60, (i % 2) * 60) for i in range(15)]
        triggered = sd.feed(60, 60)
        assert triggered

    def test_cooldown_prevents_rapid_retrigger(self):
        sd = ShakeDetector(threshold=50, cooldown_sec=10.0)
        sd.press()
        now = time.monotonic()
        sd._samples = [(now + i * 0.01, (i % 2) * 60, (i % 2) * 60) for i in range(15)]
        first = sd.feed(60, 60)
        # Second shake attempt within cooldown should not trigger
        sd._samples = [(now + i * 0.01, (i % 2) * 60, (i % 2) * 60) for i in range(15)]
        second = sd.feed(60, 60)
        assert first
        assert not second

    def test_reset(self):
        sd = ShakeDetector()
        sd.press()
        sd.reset()
        assert not sd.is_pressed
