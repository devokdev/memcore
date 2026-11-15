---
name: memcore-matrix
description: Renders the live interactive MemCore Neural Memory Matrix and Token Funnel canvas widget in chat. Use when the user asks to see MemCore status, memory graph, token savings, or when starting a session in a project using MemCore.
---

# MemCore Neural Memory Matrix Skill

Whenever the user asks to inspect memory, check tokens, or asks about MemCore in any workspace:

1. Read current memory statistics from `memcore.db`.
2. Generate the interactive HTML artifact using the template with `<canvas id="neuralCanvas">`.
3. Embed it directly in chat using:
   ```html
   <agent-embed src="file:///<artifact_path>/memcore_matrix.html"></agent-embed>
   ```
