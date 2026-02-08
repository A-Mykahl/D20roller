"""Pixel-art die rendering with Pillow and animation frame generation."""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFont

# ---------- colour palette (retro pixel-art feel) ----------
BG_COLOR = (24, 20, 37)  # deep purple-black
DIE_OUTLINE = (244, 180, 27)  # warm gold
DIE_FILL_IDLE = (58, 52, 82)  # muted violet
DIE_FILL_ROLLING = (90, 74, 120)  # lighter violet (animation)
DIE_FILL_RESULT = (38, 70, 83)  # teal-ish on result
TEXT_COLOR = (255, 255, 255)
CRIT_COLOR = (80, 220, 100)  # nat 20
FAIL_COLOR = (220, 50, 47)  # nat 1
HISTORY_BG = (34, 30, 50)

FRAME_SIZE = 160  # px, square


def _try_font(size: int) -> ImageFont.ImageFont:
    """Return a monospace / bitmap-style font, falling back to default."""
    for name in (
        "DejaVuSansMono.ttf",
        "DejaVuSans.ttf",
        "LiberationMono-Regular.ttf",
        "FreeMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# Pre-build fonts at module level (cheap, reused)
_FONT_BIG = _try_font(48)
_FONT_MED = _try_font(28)
_FONT_SMALL = _try_font(14)


# ---- D20 shape geometry (icosahedron-ish front face as a triangle) ----


def _d20_polygon(cx: int, cy: int, radius: int) -> list[tuple[int, int]]:
    """Return vertices of a d20-style equilateral triangle (point-up)."""
    pts = []
    for i in range(3):
        angle = math.radians(-90 + 120 * i)
        pts.append(
            (
                int(cx + radius * math.cos(angle)),
                int(cy + radius * math.sin(angle)),
            )
        )
    return pts


def _draw_d20_face(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    number: int | str,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
    text_color: tuple[int, int, int],
    font: ImageFont.ImageFont,
) -> None:
    """Draw a single d20 triangular face with a number centred."""
    pts = _d20_polygon(cx, cy, radius)

    # Filled triangle
    draw.polygon(pts, fill=fill, outline=outline, width=3)

    # Inner detail lines (three lines from each vertex to midpoint of opposite)
    for i in range(3):
        opp = ((i + 1) % 3, (i + 2) % 3)
        mx = (pts[opp[0]][0] + pts[opp[1]][0]) // 2
        my = (pts[opp[0]][1] + pts[opp[1]][1]) // 2
        # Draw faint guide lines
        draw.line([pts[i], (mx, my)], fill=outline, width=1)

    # Number text – centred at centroid (shifted up slightly)
    text = str(number)
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    # centroid of triangle is at (cx, cy + radius/6) roughly
    ty = cy + radius // 8
    draw.text((cx - tw // 2, ty - th // 2), text, fill=text_color, font=font)


def render_die_frame(
    number: int | str,
    *,
    size: int = FRAME_SIZE,
    fill: tuple[int, int, int] | None = None,
    is_crit: bool = False,
    is_fail: bool = False,
) -> Image.Image:
    """Render a single die-face frame as a Pillow Image."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    radius = int(size * 0.44)

    if fill is None:
        fill = DIE_FILL_IDLE
    outline = DIE_OUTLINE

    text_color = TEXT_COLOR
    if is_crit:
        text_color = CRIT_COLOR
        outline = CRIT_COLOR
    elif is_fail:
        text_color = FAIL_COLOR
        outline = FAIL_COLOR

    _draw_d20_face(draw, cx, cy, radius, number, fill, outline, text_color, _FONT_BIG)
    return img


def generate_roll_animation_frames(
    final_value: int,
    max_face: int = 20,
    num_frames: int = 16,
) -> list[Image.Image]:
    """Generate a sequence of die-face frames ending on final_value.

    Early frames show random numbers with the rolling fill colour;
    the last frame shows the final result with appropriate styling.
    """
    frames: list[Image.Image] = []
    rng = random.Random()  # non-deterministic for visual flair

    for i in range(num_frames):
        is_last = i == num_frames - 1
        if is_last:
            value = final_value
            fill = DIE_FILL_RESULT
            is_crit = final_value == max_face and max_face == 20
            is_fail = final_value == 1 and max_face == 20
        else:
            value = rng.randint(1, max(max_face, 1))
            fill = DIE_FILL_ROLLING
            is_crit = False
            is_fail = False

        frames.append(
            render_die_frame(
                value,
                fill=fill,
                is_crit=is_crit,
                is_fail=is_fail,
            )
        )

    return frames


def pil_to_photoimage(img: Image.Image):
    """Convert a Pillow Image to a Tk-compatible PhotoImage."""
    from PIL import ImageTk

    return ImageTk.PhotoImage(img)


def render_idle_die(label: str = "?", size: int = FRAME_SIZE) -> Image.Image:
    """Render the idle / waiting state die face."""
    return render_die_frame(label, size=size, fill=DIE_FILL_IDLE)
