"""
MemCore Sidecar Backend Server for Antigravity AUX Pane.
Serves index.html with live /api/metrics from memcore.db.
"""

import http.server
import json
import os
import socketserver
import sys
from urllib.parse import urlparse

from memcore.storage import SQLiteMemoryStore
from memcore.models import MemoryStatus


class MemCoreSidecarHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            db_path = os.environ.get("MEMCORE_DB_PATH", "memcore.db")
            metrics = {
                "active_tokens": 0,
                "pruned_tokens": 0,
                "savings_pct": 0.0,
                "active_memories": 0,
                "protected_count": 0,
                "memories": []
            }

            if os.path.exists(db_path):
                try:
                    store = SQLiteMemoryStore(db_path=db_path)
                    all_mems = store.list_memories(status=None, limit=200)

                    active_tokens = 0
                    archived_tokens = 0
                    active_count = 0
                    prot_count = 0
                    pruned_count = 0
                    active_items = []

                    for m in all_mems:
                        if m.status == MemoryStatus.ACTIVE:
                            active_tokens += m.token_count
                            active_count += 1
                            if m.is_protected:
                                prot_count += 1
                            active_items.append({
                                "id": m.id,
                                "type": m.memory_type.value,
                                "content": m.content,
                                "token_count": m.token_count,
                                "is_protected": m.is_protected
                            })
                        elif m.status in (MemoryStatus.ARCHIVED, MemoryStatus.SUPERSEDED):
                            archived_tokens += m.token_count
                            pruned_count += 1

                    total_life = active_tokens + archived_tokens
                    pct = (archived_tokens / total_life * 100) if total_life > 0 else 0.0

                    metrics = {
                        "active_tokens": active_tokens,
                        "pruned_tokens": archived_tokens,
                        "savings_pct": round(pct, 1),
                        "active_memories": active_count,
                        "protected_count": prot_count,
                        "memories": active_items
                    }
                except Exception as e:
                    pass

            self.wfile.write(json.dumps(metrics).encode("utf-8"))
            return

        # Serve index.html or static files
        return super().do_GET()


def main():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(cur_dir)
    port = int(os.environ.get("PORT", "52981"))

    # Reuse address
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), MemCoreSidecarHandler) as httpd:
        print(f"MemCore Sidecar serving on http://127.0.0.1:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
