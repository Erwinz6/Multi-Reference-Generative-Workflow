# Workflow Notes

This repository currently includes two public workflow examples:

- `batik_workflow_api_1.json`
  - Flux text-to-image
  - recommended default for public reproduction
  - uses prompt-driven generation

- `batik_garment_transfer_dual_reference.json`
  - dual-reference garment transfer
  - intended for appearance transfer experiments
  - may require extra ComfyUI custom nodes and local reference images

To switch workflows, update `workflow_path` in `configs/paths.json` or `configs/paths.example.json`, or set the corresponding environment variable used by the Python services.

## Default Adapter Rules

The current public `src/sdxl_service/sse_server.py` adapts workflows using a small set of default rules:

- **Prompt node support**
  - first priority: `WeiLinComfyUIPromptToLoras`
  - second priority: `CLIPTextEncode`
  - fallback: `CLIPTextEncodeFlux`

- **Seed node support**
  - first priority: `RandomNoise`
  - fallback: `KSampler`

- **Output node support**
  - reuse an existing `SaveImage` node if present
  - otherwise try to inject a `SaveImage` node by tracing the image source from `PreviewImage`

This means:

- prompt-only Flux workflows are the safest public default,
- more complex transfer workflows may still work if they expose compatible prompt and output nodes,
- custom workflows with different prompt/output node conventions may require manual adaptation in `src/sdxl_service/sse_server.py`.
