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

## Default Adapter Rules

The current public `src/sdxl_service/sse_server.py` adapts workflows using a small set of default rules:

- prompt node support: `WeiLinComfyUIPromptToLoras`, `CLIPTextEncode`, fallback `CLIPTextEncodeFlux`
- seed node support: `RandomNoise`, fallback `KSampler`
- output node support: reuse `SaveImage`, otherwise try to inject one from `PreviewImage`
