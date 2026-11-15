"""
MemCore Native Antigravity Floating Header Bar (Docked Attached Look)

This bar attaches right on top of the Antigravity prompt card:
- Matches the width of the prompt input card
- Sits flush directly on top of the input card (top-rounded only, bottom flat flush)
- Zero floating gap: Looks like an integrated top tab/header of the Antigravity prompt container
- Draggable with position memory saved locally in .memcore_hud_pos.json
- Exact matte slate palette: #1f1f24, border #2d2d38
"""

import argparse
import json
import os
import sys
import time

from memcore.storage import SQLiteMemoryStore
from memcore.models import MemoryStatus

try:
    import tkinter as tk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

CONFIG_FILE = os.path.expanduser("~/.gemini/memcore_hud_pos.json")


def load_saved_pos(default_x, default_y):
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                d = json.load(f)
                return d.get("x", default_x), d.get("y", default_y)
    except Exception:
        pass
    return default_x, default_y


def save_pos(x, y):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump({"x": x, "y": y}, f)
    except Exception:
        pass


class AntigravityAttachedHeader:
    def __init__(self, db_path: str = "memcore.db"):
        self.db_path = os.path.abspath(db_path)

        if not TKINTER_AVAILABLE:
            print("Tkinter required.")
            sys.exit(1)

        self.root = tk.Tk()
        self.root.title("Antigravity MemCore Attached Bar")

        # Frameless, Always on Top
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Transparent canvas background
        self.trans_color = "#010101"
        self.root.configure(bg=self.trans_color)
        self.root.wm_attributes("-transparentcolor", self.trans_color)

        # Exact Antigravity Matte Palette (No neon)
        self.bg_pill = "#1f1f24"          # Neutral dark gray matching chat container
        self.border_pill = "#2d2d38"      # Hairline border
        self.badge_bg = "#292933"         # Model tag pill style
        self.badge_border = "#383846"     # Muted border for badge
        
        self.text_title = "#d4d4dc"       # Soft neutral off-white
        self.text_white = "#efeff4"       # Light gray for token count
        self.text_muted = "#8a8a9a"       # Subdued secondary text
        self.dot_color = "#4ade80"        # Subdued pastel dot

        # Dimensions: Sleek header strip (matches the width and hugs the input box)
        self.width = 460
        self.height = 32

        # Default position: docked right above Antigravity chat input
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        default_x = screen_w - self.width - 65
        default_y = screen_h - self.height - 110

        pos_x, pos_y = load_saved_pos(default_x, default_y)
        self.root.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")

        # Metrics cache
        self.active_tokens = 0
        self.active_count = 0
        self.prot_count = 0
        self.pruned_pct = 0.0
        self.status_text = "Listening"

        # Draggable state
        self._drag_data = {"x": 0, "y": 0}

        self._build_canvas()
        self._poll_loop()

    def _build_canvas(self):
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.trans_color,
            highlightthickness=0,
            cursor="fleur"
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._do_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)

        self._draw_bar()

    def _draw_top_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        """Draws a shape with rounded TOP corners and flat/flush BOTTOM corners."""
        points = [
            x1 + r, y1,
            x2 - r, y1,
            x2, y1,
            x2, y1 + r,
            x2, y2,        # Flat bottom right
            x1, y2,        # Flat bottom left
            x1, y1 + r,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)

    def _draw_bar(self):
        self.canvas.delete("all")

        w = self.width
        h = self.height
        r = 10  # Corner radius matching Antigravity container

        # 1. Attached Header Container (Top rounded, flat bottom to attach flush)
        self._draw_top_rounded_rect(1, 1, w - 2, h, r, fill=self.bg_pill, outline=self.border_pill, width=1)

        # 2. Subtle Status Dot + "MemCore" title
        self.canvas.create_oval(14, 13, 19, 18, fill=self.dot_color, outline="")
        self.canvas.create_text(
            25, 16,
            text="MemCore",
            anchor="w",
            fill=self.text_title,
            font=("Segoe UI", 9, "bold")
        )

        # Hairline divider
        self.canvas.create_line(90, 8, 90, 24, fill=self.border_pill, width=1)

        # 3. Active Tokens Count & Label
        tokens_str = f"{self.active_tokens:,}"
        self.canvas.create_text(
            100, 16,
            text=tokens_str,
            anchor="w",
            fill=self.text_white,
            font=("Segoe UI", 9, "bold")
        )
        self.canvas.create_text(
            100 + (len(tokens_str) * 8) + 4, 16,
            text="tokens",
            anchor="w",
            fill=self.text_muted,
            font=("Segoe UI", 8)
        )

        # 4. Status Badge (matches Antigravity model badge style)
        badge_x = 188
        badge_w = 90
        points = [
            badge_x + 4, 5,
            badge_x + badge_w - 4, 5,
            badge_x + badge_w, 5,
            badge_x + badge_w, 26,
            badge_x, 26,
            badge_x, 5
        ]
        self.canvas.create_polygon(points, smooth=True, fill=self.badge_bg, outline=self.badge_border, width=1)

        self.canvas.create_text(
            badge_x + (badge_w // 2), 16,
            text=self.status_text,
            anchor="center",
            fill=self.text_title if self.active_count > 0 else self.text_muted,
            font=("Segoe UI", 8)
        )

        # 5. Memories & Protected Count
        prot_suffix = f" • {self.prot_count} protected" if self.prot_count > 0 else ""
        self.canvas.create_text(
            295, 16,
            text=f"{self.active_count} mems{prot_suffix}",
            anchor="w",
            fill=self.text_muted,
            font=("Segoe UI", 8)
        )

        # 6. Drag Grip Handle & Close Button
        grip_x = w - 34
        self.canvas.create_text(
            grip_x, 16,
            text="⋮⋮",
            fill=self.border_pill,
            font=("Segoe UI", 9)
        )

        close_id = self.canvas.create_text(
            w - 15, 16,
            text="✕",
            fill=self.text_muted,
            font=("Segoe UI", 8)
        )
        self.canvas.tag_bind(close_id, "<Button-1>", lambda e: self.root.destroy())

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _end_drag(self, event):
        save_pos(self.root.winfo_x(), self.root.winfo_y())

    def _poll_loop(self):
        try:
            if os.path.exists(self.db_path):
                store = SQLiteMemoryStore(db_path=self.db_path)
                mems = store.list_memories(status=None)
                self.active_tokens = sum(m.token_count for m in mems if m.status == MemoryStatus.ACTIVE)
                archived_tokens = sum(m.token_count for m in mems if m.status in (MemoryStatus.ARCHIVED, MemoryStatus.SUPERSEDED))
                self.active_count = sum(1 for m in mems if m.status == MemoryStatus.ACTIVE)
                self.prot_count = sum(1 for m in mems if m.is_protected)
                pruned_count = sum(1 for m in mems if m.status in (MemoryStatus.ARCHIVED, MemoryStatus.SUPERSEDED))

                total_life = self.active_tokens + archived_tokens
                if total_life > 0 and pruned_count > 0:
                    self.pruned_pct = round((archived_tokens / total_life) * 100, 1)
                    self.status_text = f"↓ {self.pruned_pct}% saved"
                elif self.active_count > 0:
                    self.status_text = f"{self.active_count} active"
                else:
                    self.status_text = "Listening"
            else:
                self.status_text = "Ready"

            self._draw_bar()
        except Exception:
            pass

        self.root.after(1000, self._poll_loop)

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.environ.get("MEMCORE_DB_PATH", "memcore.db"), help="Path to memcore.db")
    args = parser.parse_args()
    pill = AntigravityAttachedHeader(db_path=args.db)
    pill.run()


if __name__ == "__main__":
    main()
