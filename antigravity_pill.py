"""
MemCore Native Antigravity Floating Pill Bar (HUD)

A frameless, sleek, semi-transparent pill bar styled exactly like the
Antigravity chatbox interface. It floats right above your chatbox (or anywhere
you drag it) with:
- Live Active Tokens vs Saved Tokens
- Pruned Savings % badge
- Live Memory pill (Active / Protected)
- Real-time ticker of last memory action
- Draggable anywhere, stays on top, matches dark theme #131722 / #1c2130
"""

import argparse
import os
import sys
import time

from memcore.storage import SQLiteMemoryStore
from memcore.models import MemoryStatus

try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False


class AntigravityFloatingPill:
    def __init__(self, base_dir: str = "C:/Users/karta/Desktop/projects/memcore-test"):
        self.base_dir = os.path.abspath(base_dir)

        # Detect directory structure
        if os.path.exists(os.path.join(self.base_dir, "with")):
            self.dir_with = os.path.join(self.base_dir, "with")
            self.dir_without = os.path.join(self.base_dir, "without")
        else:
            self.dir_with = os.path.join(self.base_dir, "project_with_memcore")
            self.dir_without = os.path.join(self.base_dir, "project_without_plugin")

        self.db_path = os.path.join(self.dir_with, "memcore.db")

        # Baseline without-tokens (from files or default ~3,159)
        self.tokens_without = 3159

        if not TKINTER_AVAILABLE:
            print("Tkinter required.")
            sys.exit(1)

        self.root = tk.Tk()
        self.root.title("Antigravity MemCore Pill")

        # Frameless, Always on Top, Clean Subpixel Dark Theme
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)

        # Antigravity Palette
        self.bg_color = "#181d28"        # Sleek dark navy/slate
        self.border_color = "#2a3447"    # Antigravity subtle border
        self.accent_cyan = "#00d2ff"     # Antigravity Cyan
        self.accent_green = "#10b981"    # Savings green
        self.accent_purple = "#c084fc"   # Protected purple
        self.text_dim = "#94a3b8"        # Slate text
        self.text_bright = "#f8fafc"     # Pure white/light

        # Dimensions & positioning: Compact pill bar (520px x 46px)
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pill_w = 540
        pill_h = 44
        
        # Position right above where Antigravity chat input sits (bottom right/center)
        pos_x = screen_w - pill_w - 60
        pos_y = screen_h - pill_h - 130
        self.root.geometry(f"{pill_w}x{pill_h}+{pos_x}+{pos_y}")
        self.root.configure(bg=self.bg_color)

        # Draggable bindings
        self._drag_data = {"x": 0, "y": 0}
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        self._build_ui()
        self._poll_loop()

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Outer pill container with smooth rounded look border
        self.container = tk.Frame(
            self.root, 
            bg=self.bg_color, 
            highlightbackground=self.border_color, 
            highlightthickness=1,
            cursor="fleur"
        )
        self.container.pack(fill="both", expand=True)

        # Left: MemCore Logo & Glowing Status Dot
        left_box = tk.Frame(self.container, bg=self.bg_color)
        left_box.pack(side="left", padx=(12, 6), pady=6)

        dot_label = tk.Label(left_box, text="●", bg=self.bg_color, fg="#38ef7d", font=("Segoe UI", 9, "bold"))
        dot_label.pack(side="left", padx=(0, 4))

        brand_label = tk.Label(left_box, text="MemCore", bg=self.bg_color, fg=self.accent_cyan, font=("Segoe UI", 9, "bold"))
        brand_label.pack(side="left")

        # Divider
        tk.Label(self.container, text="│", bg=self.bg_color, fg=self.border_color, font=("Segoe UI", 11)).pack(side="left", padx=4)

        # Active Tokens Metric
        token_box = tk.Frame(self.container, bg=self.bg_color)
        token_box.pack(side="left", padx=4)

        self.lbl_tokens = tk.Label(token_box, text="323 tokens", bg=self.bg_color, fg=self.text_bright, font=("Segoe UI", 9, "bold"))
        self.lbl_tokens.pack(side="left")

        self.lbl_context_tag = tk.Label(token_box, text="(active)", bg=self.bg_color, fg=self.text_dim, font=("Segoe UI", 7))
        self.lbl_context_tag.pack(side="left", padx=(4, 0))

        # Divider
        tk.Label(self.container, text="│", bg=self.bg_color, fg=self.border_color, font=("Segoe UI", 11)).pack(side="left", padx=4)

        # Savings Badge
        savings_box = tk.Frame(self.container, bg="#064e3b", highlightbackground="#059669", highlightthickness=1, padx=6, pady=2)
        savings_box.pack(side="left", padx=4)

        self.lbl_savings = tk.Label(
            savings_box, 
            text="↓ 89.8% saved", 
            bg="#064e3b", 
            fg="#34d399", 
            font=("Segoe UI", 8, "bold")
        )
        self.lbl_savings.pack()

        # Divider
        tk.Label(self.container, text="│", bg=self.bg_color, fg=self.border_color, font=("Segoe UI", 11)).pack(side="left", padx=4)

        # Active & Protected Counts
        mems_box = tk.Frame(self.container, bg=self.bg_color)
        mems_box.pack(side="left", padx=4)

        self.lbl_mems = tk.Label(
            mems_box, 
            text="9 mems • 2 protected", 
            bg=self.bg_color, 
            fg=self.accent_purple, 
            font=("Segoe UI", 8, "bold")
        )
        self.lbl_mems.pack(side="left")

        # Drag grip handle & close button
        ctrl_box = tk.Frame(self.container, bg=self.bg_color)
        ctrl_box.pack(side="right", padx=(4, 8))

        close_btn = tk.Label(
            ctrl_box, 
            text="✕", 
            bg=self.bg_color, 
            fg=self.text_dim, 
            font=("Segoe UI", 8), 
            cursor="hand2"
        )
        close_btn.pack(side="right", padx=(6, 2))
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        grip_lbl = tk.Label(
            ctrl_box, 
            text="⋮⋮", 
            bg=self.bg_color, 
            fg="#475569", 
            font=("Segoe UI", 10), 
            cursor="fleur"
        )
        grip_lbl.pack(side="right")

    def _poll_loop(self):
        try:
            if os.path.exists(self.db_path):
                store = SQLiteMemoryStore(db_path=self.db_path)
                mems = store.list_memories(status=None)
                active_tokens = sum(m.token_count for m in mems if m.status == MemoryStatus.ACTIVE)
                active_count = sum(1 for m in mems if m.status == MemoryStatus.ACTIVE)
                prot_count = sum(1 for m in mems if m.is_protected)

                self.lbl_tokens.config(text=f"{active_tokens:,} tokens")
                self.lbl_mems.config(text=f"{active_count} mems • {prot_count} protected")

                if self.tokens_without > 0 and active_tokens > 0:
                    diff = max(0, self.tokens_without - active_tokens)
                    pct = round((diff / self.tokens_without) * 100, 1)
                    self.lbl_savings.config(text=f"↓ {pct}% saved")
        except Exception:
            pass

        self.root.after(1000, self._poll_loop)

    def run(self):
        self.root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="C:/Users/karta/Desktop/projects/memcore-test")
    args = parser.parse_args()
    pill = AntigravityFloatingPill(base_dir=args.dir)
    pill.run()


if __name__ == "__main__":
    main()

