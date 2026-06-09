# ComfyUI Setup

1. Install and launch ComfyUI locally.
2. Make sure the workflow file in `workflows/` is compatible with your installed nodes.
3. Confirm the output directory used by ComfyUI matches the path expected by `sse_server.py` and `ue_listener.py`.
4. Choose the workflow through `configs/paths.json` or `configs/paths.example.json`.
5. Start the MCP SSE service after ComfyUI is available.

Notes:

- `batik_workflow_api_1.json` is the simpler public default.
- `batik_garment_transfer_dual_reference.json` may require extra custom nodes and local reference images.
- The default Python-side workflow adapter currently injects prompt, seed, and `SaveImage` only for a limited set of supported node patterns.
- If the selected workflow relies on custom nodes, install them before attempting reproduction.
