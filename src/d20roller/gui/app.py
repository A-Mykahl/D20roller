"""Main Tk application for the D20roller pixel-art GUI."""

from __future__ import annotations

import datetime
import enum
import tkinter as tk
from dataclasses import dataclass

from d20roller.gui.input import ShakeDetector
from d20roller.gui.render import (
    BG_COLOR,
    CRIT_COLOR,
    DIE_FILL_IDLE,
    FAIL_COLOR,
    FRAME_SIZE,
    HISTORY_BG,
    TEXT_COLOR,
    generate_roll_animation_frames,
    pil_to_photoimage,
    render_idle_die,
)
from d20roller.roller import RollResult, roll

# ---------- constants ----------
WINDOW_TITLE = "D20 Roller"
WINDOW_WIDTH = 480
WINDOW_HEIGHT = 620
ANIM_FRAME_MS = 40  # ~25 fps
MAX_HISTORY = 10


def _rgb(color: tuple[int, int, int]) -> str:
    return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"


BG_HEX = _rgb(BG_COLOR)
HIST_BG_HEX = _rgb(HISTORY_BG)
TEXT_HEX = _rgb(TEXT_COLOR)
CRIT_HEX = _rgb(CRIT_COLOR)
FAIL_HEX = _rgb(FAIL_COLOR)
GOLD_HEX = _rgb((244, 180, 27))
IDLE_HEX = _rgb(DIE_FILL_IDLE)


class State(enum.Enum):
    IDLE = "idle"
    ROLLING = "rolling"


class RollMode(enum.Enum):
    NORMAL = "Normal"
    ADVANTAGE = "Advantage"
    DISADVANTAGE = "Disadvantage"


@dataclass
class HistoryEntry:
    timestamp: str
    expression: str
    result: RollResult


class D20App:
    """The main GUI application."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_HEX)
        self.root.resizable(False, False)

        self.state = State.IDLE
        self.mode = RollMode.NORMAL
        self.history: list[HistoryEntry] = []
        self.shake = ShakeDetector()

        # Animation state
        self._anim_frames: list = []
        self._anim_index: int = 0
        self._anim_after_id: str | None = None
        self._pending_result: RollResult | None = None

        # Keep references to PhotoImages to prevent GC
        self._photo_refs: list = []

        self._build_ui()
        self._show_idle_die()

    # ---- UI construction ----

    def _build_ui(self) -> None:
        # --- expression input row ---
        input_frame = tk.Frame(self.root, bg=BG_HEX)
        input_frame.pack(pady=(12, 4), padx=16, fill=tk.X)

        tk.Label(
            input_frame,
            text="Roll:",
            bg=BG_HEX,
            fg=TEXT_HEX,
            font=("TkFixedFont", 12),
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.expr_var = tk.StringVar(value="1d20")
        self.expr_entry = tk.Entry(
            input_frame,
            textvariable=self.expr_var,
            font=("TkFixedFont", 14),
            width=16,
            bg=IDLE_HEX,
            fg=TEXT_HEX,
            insertbackground=TEXT_HEX,
            relief=tk.FLAT,
            bd=4,
        )
        self.expr_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.expr_entry.bind("<Return>", lambda _e: self._do_roll())

        # --- mode toggle row ---
        mode_frame = tk.Frame(self.root, bg=BG_HEX)
        mode_frame.pack(pady=(4, 8))

        self._mode_buttons: dict[RollMode, tk.Button] = {}
        for m in RollMode:
            btn = tk.Button(
                mode_frame,
                text=m.value,
                width=12,
                font=("TkFixedFont", 10),
                bg=IDLE_HEX,
                fg=TEXT_HEX,
                activebackground=GOLD_HEX,
                relief=tk.FLAT,
                bd=2,
                command=lambda mode=m: self._set_mode(mode),
            )
            btn.pack(side=tk.LEFT, padx=4)
            self._mode_buttons[m] = btn
        self._highlight_mode_button()

        # --- die canvas (click / shake area) ---
        self.canvas = tk.Canvas(
            self.root,
            width=FRAME_SIZE + 40,
            height=FRAME_SIZE + 40,
            bg=BG_HEX,
            highlightthickness=0,
        )
        self.canvas.pack(pady=(4, 4))
        self._die_image_id = self.canvas.create_image(
            (FRAME_SIZE + 40) // 2,
            (FRAME_SIZE + 40) // 2,
            anchor=tk.CENTER,
        )

        # Click to roll
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<B1-Motion>", self._on_motion)

        # --- result label ---
        self.result_var = tk.StringVar(value="Click the die to roll!")
        self.result_label = tk.Label(
            self.root,
            textvariable=self.result_var,
            bg=BG_HEX,
            fg=GOLD_HEX,
            font=("TkFixedFont", 22, "bold"),
        )
        self.result_label.pack(pady=(0, 2))

        # --- detail label (breakdown) ---
        self.detail_var = tk.StringVar(value="")
        self.detail_label = tk.Label(
            self.root,
            textvariable=self.detail_var,
            bg=BG_HEX,
            fg=TEXT_HEX,
            font=("TkFixedFont", 11),
        )
        self.detail_label.pack(pady=(0, 8))

        # --- history listbox ---
        hist_label = tk.Label(
            self.root,
            text="History",
            bg=BG_HEX,
            fg=GOLD_HEX,
            font=("TkFixedFont", 10, "bold"),
        )
        hist_label.pack(anchor=tk.W, padx=20)

        self.history_box = tk.Listbox(
            self.root,
            height=MAX_HISTORY,
            width=52,
            bg=HIST_BG_HEX,
            fg=TEXT_HEX,
            font=("TkFixedFont", 10),
            selectbackground=IDLE_HEX,
            relief=tk.FLAT,
            bd=4,
        )
        self.history_box.pack(padx=20, pady=(2, 12), fill=tk.X)

    # ---- mode switching ----

    def _set_mode(self, mode: RollMode) -> None:
        self.mode = mode
        # Update expression to match mode preset if it was a simple d20 roll
        current = self.expr_var.get().strip()
        presets = {"1d20", "2d20kh1", "2d20kl1"}
        if current in presets or not current:
            if mode == RollMode.NORMAL:
                self.expr_var.set("1d20")
            elif mode == RollMode.ADVANTAGE:
                self.expr_var.set("2d20kh1")
            elif mode == RollMode.DISADVANTAGE:
                self.expr_var.set("2d20kl1")
        self._highlight_mode_button()

    def _highlight_mode_button(self) -> None:
        for m, btn in self._mode_buttons.items():
            if m == self.mode:
                btn.configure(bg=GOLD_HEX, fg=BG_HEX)
            else:
                btn.configure(bg=IDLE_HEX, fg=TEXT_HEX)

    # ---- rolling logic ----

    def _effective_notation(self) -> str:
        return self.expr_var.get().strip() or "1d20"

    def _do_roll(self) -> None:
        if self.state == State.ROLLING:
            return  # ignore if already animating

        notation = self._effective_notation()
        try:
            result = roll(notation)
        except ValueError as e:
            self.result_var.set("Error")
            self.detail_var.set(str(e))
            return

        self._pending_result = result
        self._start_animation(result)

    def _start_animation(self, result: RollResult) -> None:
        self.state = State.ROLLING

        # Determine max face for animation (use first dice term's sides, default 20)
        max_face = 20
        for part in result.parts:
            if hasattr(part, "expr"):
                max_face = part.expr.sides
                break

        frames = generate_roll_animation_frames(
            final_value=result.total,
            max_face=max_face,
            num_frames=16,
        )

        self._photo_refs.clear()
        self._anim_frames = []
        for f in frames:
            photo = pil_to_photoimage(f)
            self._photo_refs.append(photo)
            self._anim_frames.append(photo)

        self._anim_index = 0
        self._tick_animation()

    def _tick_animation(self) -> None:
        if self._anim_index >= len(self._anim_frames):
            self._finish_animation()
            return

        photo = self._anim_frames[self._anim_index]
        self.canvas.itemconfigure(self._die_image_id, image=photo)
        self._anim_index += 1

        # Speed ramp: start fast, slow down towards the end
        remaining = len(self._anim_frames) - self._anim_index
        if remaining > 8:
            delay = 30
        elif remaining > 4:
            delay = 50
        else:
            delay = 80

        self._anim_after_id = self.root.after(delay, self._tick_animation)

    def _finish_animation(self) -> None:
        self.state = State.IDLE
        result = self._pending_result
        if result is None:
            return

        total = result.total

        # Colour the result based on nat 20 / nat 1
        is_nat20 = False
        is_nat1 = False
        for part in result.parts:
            if hasattr(part, "expr") and part.expr.sides == 20:
                if len(part.kept) == 1:
                    if part.kept[0] == 20:
                        is_nat20 = True
                    elif part.kept[0] == 1:
                        is_nat1 = True

        if is_nat20:
            self.result_label.configure(fg=CRIT_HEX)
            self.result_var.set(f"NAT 20!  ({total})")
        elif is_nat1:
            self.result_label.configure(fg=FAIL_HEX)
            self.result_var.set(f"NAT 1...  ({total})")
        else:
            self.result_label.configure(fg=GOLD_HEX)
            self.result_var.set(str(total))

        self.detail_var.set(str(result))

        # Add to history
        now = datetime.datetime.now().strftime("%H:%M:%S")
        entry = HistoryEntry(timestamp=now, expression=result.parsed.raw, result=result)
        self.history.insert(0, entry)
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[:MAX_HISTORY]
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.history_box.delete(0, tk.END)
        for entry in self.history:
            line = f"[{entry.timestamp}]  {entry.expression} = {entry.result.total}"
            self.history_box.insert(tk.END, line)

    def _show_idle_die(self) -> None:
        img = render_idle_die()
        photo = pil_to_photoimage(img)
        self._photo_refs = [photo]
        self.canvas.itemconfigure(self._die_image_id, image=photo)

    # ---- mouse input handlers ----

    def _on_press(self, event: tk.Event) -> None:
        if self.state == State.ROLLING:
            return
        self.shake.press()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self.shake.is_pressed
        self.shake.release()
        # Simple click (press + release without triggering shake) = roll
        if was_pressed and self.state == State.IDLE:
            self._do_roll()

    def _on_motion(self, event: tk.Event) -> None:
        if self.state == State.ROLLING:
            return
        if self.shake.feed(event.x, event.y):
            # Shake triggered a roll
            self._do_roll()


def main() -> None:
    root = tk.Tk()
    D20App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
