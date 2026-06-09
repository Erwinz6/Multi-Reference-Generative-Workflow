# ComfyUI Setup

1. Install and launch ComfyUI locally.
2. Make sure the workflow file in `workflows/` is compatible with your installed nodes.
3. Confirm the output directory used by ComfyUI matches the path expected by `sse_server.py` and `ue_listener.py`.
4. Start the MCP SSE service after ComfyUI is available.

If the workflow relies on custom nodes, install them before attempting reproduction.
