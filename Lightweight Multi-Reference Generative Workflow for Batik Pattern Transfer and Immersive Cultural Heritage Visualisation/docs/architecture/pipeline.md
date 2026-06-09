# Pipeline Overview

This project implements a lightweight multi-stage workflow:

1. A user or batch script triggers `/generate_then_update`.
2. The orchestrator generates a run identifier and dispatches the request.
3. The MCP SSE service submits the prompt to ComfyUI / SDXL.
4. The generated image path is forwarded by the bridge service.
5. Unreal Engine receives the image path and schedules the import task.
6. The image is imported as a texture and applied to the target material parameter.
7. The viewport is refreshed so the final result becomes visible in the UE scene.

The codebase is separated into the following layers:

- orchestration,
- generation,
- bridge transfer,
- UE display update,
- experiment analysis.
