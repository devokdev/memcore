"""
MemCore CLI - One-command setup & activation for any project.

Usage:
  memcore init        # Initializes MemCore, registers global Antigravity/MCP plugin, and launches HUD
  memcore hud         # Launches floating token counter pill for current project
  memcore server      # Runs the MCP stdio server
  memcore dashboard   # Launches web dashboard on http://127.0.0.1:8000
"""

import argparse
import json
import os
import sys
import subprocess

PLUGIN_DIR_NAME = "memcore"


def get_global_antigravity_dir() -> str:
    user_home = os.path.expanduser("~")
    return os.path.join(user_home, ".gemini")


def setup_global_antigravity_plugin(force: bool = False):
    """Installs MemCore as a standard global Antigravity plugin under ~/.gemini/config/plugins/memcore/"""
    gemini_dir = get_global_antigravity_dir()
    plugins_dir = os.path.join(gemini_dir, "config", "plugins")
    memcore_plugin_dir = os.path.join(plugins_dir, PLUGIN_DIR_NAME)

    os.makedirs(memcore_plugin_dir, exist_ok=True)
    os.makedirs(os.path.join(memcore_plugin_dir, "rules"), exist_ok=True)

    # 1. plugin.json
    plugin_manifest = {
        "name": "memcore",
        "description": "Persistent memory, risk-aware MemGC, and real-time floating token counter HUD for coding agents.",
        "version": "0.1.0",
        "author": "MemCore Team"
    }
    with open(os.path.join(memcore_plugin_dir, "plugin.json"), "w", encoding="utf-8") as f:
        json.dump(plugin_manifest, f, indent=2)

    # 2. mcp_config.json (Launches python -m memcore.mcp_server)
    python_exe = sys.executable
    mcp_config = {
        "mcpServers": {
            "memcore": {
                "command": python_exe,
                "args": ["-m", "memcore.mcp_server"],
                "env": {
                    "MEMCORE_DB_PATH": "memcore.db",
                    "MEMCORE_REPO_ROOT": "."
                }
            }
        }
    }
    with open(os.path.join(memcore_plugin_dir, "mcp_config.json"), "w", encoding="utf-8") as f:
        json.dump(mcp_config, f, indent=2)

    # 3. rules/AGENTS.md - System prompt protocol for Antigravity & AI agents
    rules_content = """# MemCore Memory Protocol
You are connected to MemCore persistent memory.
- At the start of coding tasks, call `memory_context_build(task_query=...)` to retrieve verified project rules within token budget.
- Whenever learning an architectural invariant, security requirement, or bug fix, call `memory_add(...)`.
- For critical rules (security keys, database schemas, payment contracts), set `is_protected=True`.
- Call `memory_gc()` when cleaning up scratchpad notes or obsolete code.
"""
    with open(os.path.join(memcore_plugin_dir, "rules", "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write(rules_content)

    # 4. Copy native sidecar UI panel if available
    src_sidecar = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sidecars", "memcore_panel")
    dest_sidecar = os.path.join(memcore_plugin_dir, "sidecars", "memcore_panel")
    if os.path.exists(src_sidecar):
        import shutil
        os.makedirs(dest_sidecar, exist_ok=True)
        for item in os.listdir(src_sidecar):
            s = os.path.join(src_sidecar, item)
            d = os.path.join(dest_sidecar, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)

    # Also update global ~/.gemini/config/mcp_config.json as standard fallback
    global_mcp_path = os.path.join(gemini_dir, "config", "mcp_config.json")
    existing_mcp = {}
    if os.path.exists(global_mcp_path):
        try:
            with open(global_mcp_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    existing_mcp = json.loads(content)
        except Exception:
            existing_mcp = {}

    if "mcpServers" not in existing_mcp:
        existing_mcp["mcpServers"] = {}

    existing_mcp["mcpServers"]["memcore"] = mcp_config["mcpServers"]["memcore"]

    with open(global_mcp_path, "w", encoding="utf-8") as f:
        json.dump(existing_mcp, f, indent=2)

    return memcore_plugin_dir


def init_project(target_dir: str = "."):
    """Sets up MemCore in the target directory, registers global plugin, and starts the HUD."""
    target_path = os.path.abspath(target_dir)
    print(f"\n=======================================================")
    print(f"       🧠 MemCore Plugin & HUD One-Step Activator       ")
    print(f"=======================================================")
    print(f"[1/3] Activating MemCore in project: {target_path}")

    # Create local database if not exists
    db_path = os.path.join(target_path, "memcore.db")
    from memcore.storage import SQLiteMemoryStore
    store = SQLiteMemoryStore(db_path=db_path)
    print(f"      ✓ Local memory store ready: {db_path}")

    # Register global Antigravity plugin
    print(f"[2/3] Registering global Antigravity & MCP plugin...")
    plugin_dir = setup_global_antigravity_plugin()
    print(f"      ✓ Installed plugin in: {plugin_dir}")
    print(f"      ✓ Global MCP configuration updated.")

    # Launch HUD
    print(f"[3/3] Launching Floating Antigravity Token HUD...")
    launch_hud(db_path=db_path, wait=False)
    print(f"\n✨ MemCore is now ACTIVE for this project!")
    print(f"   - Antigravity will automatically use MemCore MCP tools.")
    print(f"   - Floating token pill is active above your chatbox.")
    print(f"=======================================================\n")


def launch_hud(db_path: str = "memcore.db", wait: bool = True):
    cmd = [sys.executable, "-m", "memcore.pill", "--db", os.path.abspath(db_path)]
    if wait:
        subprocess.run(cmd)
    else:
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x00000008 | 0x00000200
        subprocess.Popen(
            cmd,
            creationflags=creationflags,
            close_fds=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL
        )


def main():
    parser = argparse.ArgumentParser(description="MemCore CLI")
    subparsers = parser.add_subparsers(dest="command")

    # init
    p_init = subparsers.add_parser("init", help="Initialize MemCore in this project, register plugin & launch HUD")
    p_init.add_argument("directory", nargs="?", default=".", help="Target project directory")

    # hud
    p_hud = subparsers.add_parser("hud", help="Launch the floating visual token HUD pill")
    p_hud.add_argument("--db", default="memcore.db", help="Path to memcore.db")

    # server
    p_srv = subparsers.add_parser("server", help="Run MCP stdio server")

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="Run web dashboard on port 8000")

    args = parser.parse_args()

    if args.command == "init" or args.command is None:
        init_project(getattr(args, "directory", "."))
    elif args.command == "hud":
        launch_hud(db_path=args.db, wait=True)
    elif args.command == "server":
        from memcore.mcp_server import mcp_server
        mcp_server.run()
    elif args.command == "dashboard":
        import uvicorn
        uvicorn.run("memcore.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()

