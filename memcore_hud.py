"""
MemCore Live Visual HUD (Desktop Overlay & Terminal Live Monitor)

Features:
- Floating, always-on-top, draggable desktop HUD widget (Tkinter)
- Terminal Live HUD fallback / companion using Rich
- Real-time token tracking: Active tokens, GC pruned tokens, Savings %, Memories count
- Live Token Tester / Estimator: Type or paste any prompt to see tiktoken count & savings instantly
"""

import argparse
import os
import sys
import threading
import time
from typing import Dict, Any, Optional

from memcore.storage import SQLiteMemoryStore
from memcore.models import MemoryStatus
from memcore.tokenizer import count_tokens

try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.layout import Layout
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def fetch_token_metrics(db_path: str = "memcore.db") -> Dict[str, Any]:
    """Fetches real-time token metrics directly from SQLite store."""
    if not os.path.exists(db_path):
        return {
            "exists": False,
            "active_tokens": 0,
            "archived_tokens": 0,
            "pruned_tokens": 0,
            "total_lifetime_tokens": 0,
            "savings_pct": 0.0,
            "active_memories": 0,
            "protected_count": 0,
            "archived_memories": 0,
            "last_event": "Waiting for MemCore activity...",
        }

    try:
        store = SQLiteMemoryStore(db_path=db_path)
        memories = store.list_memories(status=None, limit=5000)
        logs = store.get_audit_logs(limit=1)

        active_tokens = 0
        archived_tokens = 0
        active_count = 0
        archived_count = 0
        protected_count = 0

        for m in memories:
            if m.status == MemoryStatus.ACTIVE:
                active_tokens += m.token_count
                active_count += 1
                if m.is_protected:
                    protected_count += 1
            elif m.status in (MemoryStatus.ARCHIVED, MemoryStatus.SUPERSEDED):
                archived_tokens += m.token_count
                archived_count += 1

        total_lifetime = active_tokens + archived_tokens
        savings_pct = (archived_tokens / total_lifetime * 100) if total_lifetime > 0 else 0.0

        last_event = "Idle"
        if logs:
            l = logs[0]
            last_event = f"{l.action} ({l.reason or 'by ' + l.actor})"

        return {
            "exists": True,
            "active_tokens": active_tokens,
            "archived_tokens": archived_tokens,
            "pruned_tokens": archived_tokens,
            "total_lifetime_tokens": total_lifetime,
            "savings_pct": round(savings_pct, 1),
            "active_memories": active_count,
            "protected_count": protected_count,
            "archived_memories": archived_count,
            "last_event": last_event,
        }
    except Exception as e:
        return {
            "exists": True,
            "active_tokens": 0,
            "archived_tokens": 0,
            "pruned_tokens": 0,
            "total_lifetime_tokens": 0,
            "savings_pct": 0.0,
            "active_memories": 0,
            "protected_count": 0,
            "archived_memories": 0,
            "last_event": f"Error: {e}",
        }


# =====================================================================
# 1. FLOATING ALWAYS-ON-TOP DESKTOP HUD (Tkinter)
# =====================================================================
class FloatingTokenHUD:
    def __init__(self, db_path: str = "memcore.db", poll_interval_ms: int = 1000):
        self.db_path = db_path
        self.poll_interval_ms = poll_interval_ms
        self.root = tk.Tk()
        self.root.title("MemCore Token HUD")
        
        # Window attributes: Frameless, Always on Top, Sleek Dark Theme
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)

        # Initial position: top right corner
        screen_w = self.root.winfo_screenwidth()
        self.width = 340
        self.height = 220
        self.root.geometry(f"{self.width}x{self.height}+{screen_w - self.width - 24}+40")
        self.root.configure(bg="#0b0f19")

        # Make window draggable
        self._drag_data = {"x": 0, "y": 0}
        self.root.bind("<ButtonPress-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._do_drag)

        self._build_ui()
        self._update_loop()

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _do_drag(self, event):
        x = self.root.winfo_x() + (event.x - self._drag_data["x"])
        y = self.root.winfo_y() + (event.y - self._drag_data["y"])
        self.root.geometry(f"+{x}+{y}")

    def _build_ui(self):
        # Outer container with border
        container = tk.Frame(self.root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1)
        container.pack(fill="both", expand=True)

        # Header Title Bar
        header = tk.Frame(container, bg="#161b22")
        header.pack(fill="x", padx=0, pady=0)

        title_lbl = tk.Label(header, text="🧠 MEMCORE LIVE HUD", bg="#161b22", fg="#00d2ff", font=("Segoe UI", 9, "bold"))
        title_lbl.pack(side="left", padx=10, pady=6)

        close_btn = tk.Label(header, text="✕", bg="#161b22", fg="#8b949e", font=("Segoe UI", 9, "bold"), cursor="hand2")
        close_btn.pack(side="right", padx=10, pady=6)
        close_btn.bind("<Button-1>", lambda e: self.root.destroy())

        # Main stats row
        stats_frame = tk.Frame(container, bg="#0d1117")
        stats_frame.pack(fill="x", padx=12, pady=10)

        # Active Tokens Column
        col1 = tk.Frame(stats_frame, bg="#0d1117")
        col1.pack(side="left", expand=True)
        tk.Label(col1, text="ACTIVE TOKENS", bg="#0d1117", fg="#8b949e", font=("Segoe UI", 7, "bold")).pack()
        self.lbl_tokens = tk.Label(col1, text="0", bg="#0d1117", fg="#10b981", font=("Segoe UI", 18, "bold"))
        self.lbl_tokens.pack()

        # Divider
        tk.Label(stats_frame, text="|", bg="#0d1117", fg="#30363d", font=("Segoe UI", 16)).pack(side="left", padx=6)

        # Savings % Column
        col2 = tk.Frame(stats_frame, bg="#0d1117")
        col2.pack(side="left", expand=True)
        tk.Label(col2, text="PRUNED SAVINGS", bg="#0d1117", fg="#8b949e", font=("Segoe UI", 7, "bold")).pack()
        self.lbl_savings = tk.Label(col2, text="0.0%", bg="#0d1117", fg="#a855f7", font=("Segoe UI", 18, "bold"))
        self.lbl_savings.pack()

        # Secondary info row
        info_frame = tk.Frame(container, bg="#161b22", padx=10, pady=6)
        info_frame.pack(fill="x", padx=10, pady=2)

        self.lbl_memories = tk.Label(
            info_frame, 
            text="Active Mems: 0  •  Protected: 0  •  Pruned: 0", 
            bg="#161b22", 
            fg="#c9d1d9", 
            font=("Segoe UI", 8)
        )
        self.lbl_memories.pack(anchor="w")

        # Quick Live Scratchpad Input
        input_frame = tk.Frame(container, bg="#0d1117")
        input_frame.pack(fill="x", padx=10, pady=8)

        self.entry_var = tk.StringVar()
        self.entry_var.trace_add("write", self._on_text_change)
        
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.entry_var,
            bg="#21262d",
            fg="#f0f6fc",
            insertbackground="#00d2ff",
            relief="flat",
            font=("Segoe UI", 8),
            highlightbackground="#30363d",
            highlightthickness=1
        )
        self.entry.pack(fill="x", ipady=3)
        self.entry.insert(0, "Test token counter here: paste any text...")

        self.lbl_input_tokens = tk.Label(
            container, 
            text="Type or paste above to count tokens in real time (tiktoken)", 
            bg="#0d1117", 
            fg="#6e7681", 
            font=("Segoe UI", 7)
        )
        self.lbl_input_tokens.pack(anchor="w", padx=12, pady=(0, 6))

    def _on_text_change(self, *args):
        val = self.entry_var.get().strip()
        if not val or val == "Test token counter here: paste any text...":
            self.lbl_input_tokens.config(text="Type or paste above to count tokens in real time (tiktoken)")
            return
        tokens, is_est = count_tokens(val)
        suffix = " (est)" if is_est else " (cl100k_base)"
        self.lbl_input_tokens.config(
            text=f"Prompt count: {tokens} tokens{suffix} | Char count: {len(val)}", 
            fg="#58a6ff"
        )

    def _update_loop(self):
        try:
            m = fetch_token_metrics(self.db_path)
            self.lbl_tokens.config(text=f"{m['active_tokens']:,}")
            self.lbl_savings.config(text=f"{m['savings_pct']}%")
            self.lbl_memories.config(
                text=f"Active: {m['active_memories']}  •  Protected: {m['protected_count']}  •  Pruned: {m['archived_memories']}"
            )
        except Exception:
            pass
        self.root.after(self.poll_interval_ms, self._update_loop)

    def run(self):
        self.root.mainloop()


# =====================================================================
# 2. TERMINAL LIVE HUD (Rich)
# =====================================================================
def run_terminal_hud(db_path: str = "memcore.db", poll_sec: float = 1.0):
    console = Console()
    if not RICH_AVAILABLE:
        console.print("[red]Rich is required for terminal HUD mode.[/red]")
        return

    def make_hud_renderable() -> Panel:
        m = fetch_token_metrics(db_path)

        table = Table(show_header=True, header_style="bold cyan", expand=True)
        table.add_column("Active Tokens", justify="center", style="green bold")
        table.add_column("Pruned / Saved", justify="center", style="magenta bold")
        table.add_column("GC Savings %", justify="center", style="bold yellow")
        table.add_column("Active Mems", justify="center", style="cyan")
        table.add_column("Protected", justify="center", style="bold blue")

        table.add_row(
            f"{m['active_tokens']:,}",
            f"{m['pruned_tokens']:,}",
            f"{m['savings_pct']}%",
            str(m['active_memories']),
            str(m['protected_count'])
        )

        sub_text = Text()
        sub_text.append(f"\nDatabase: {os.path.abspath(db_path)}\n", style="dim")
        sub_text.append(f"Last Event: {m['last_event']}\n", style="italic white")
        sub_text.append("Monitoring real-time token events from MemCore & AI coding agent... (Ctrl+C to exit)", style="dim green")

        layout = Layout()
        layout.split_column(
            Layout(table, size=4),
            Layout(sub_text, size=4)
        )

        return Panel(
            layout,
            title="[bold cyan]🧠 MemCore Live Token Counter & HUD[/bold cyan]",
            border_style="bright_blue",
            padding=(1, 2)
        )

    with Live(make_hud_renderable(), refresh_per_second=int(1 / poll_sec), console=console) as live:
        try:
            while True:
                time.sleep(poll_sec)
                live.update(make_hud_renderable())
        except KeyboardInterrupt:
            pass


# =====================================================================
# MAIN ENTRYPOINT
# =====================================================================
def main():
    parser = argparse.ArgumentParser(description="MemCore Visual Token Counter & HUD")
    parser.add_argument("--mode", choices=["gui", "terminal", "both"], default="gui", help="HUD display mode")
    parser.add_argument("--db", default="memcore.db", help="Path to memcore.db")
    parser.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds")

    args = parser.parse_args()

    if args.mode == "terminal" or (args.mode == "gui" and not TKINTER_AVAILABLE):
        run_terminal_hud(db_path=args.db, poll_sec=args.interval)
    elif args.mode == "both":
        # Launch terminal HUD in background thread and run GUI in main thread
        t = threading.Thread(target=run_terminal_hud, args=(args.db, args.interval), daemon=True)
        t.start()
        hud = FloatingTokenHUD(db_path=args.db, poll_interval_ms=int(args.interval * 1000))
        hud.run()
    else:
        hud = FloatingTokenHUD(db_path=args.db, poll_interval_ms=int(args.interval * 1000))
        hud.run()


if __name__ == "__main__":
    main()

