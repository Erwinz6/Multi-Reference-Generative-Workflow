<div align="center">

# Lightweight Multi-Reference Generative Workflow for Batik Pattern Transfer and Immersive Cultural Heritage Visualisation

**A thesis-aligned public release for batik-aware lightweight generation, dual-reference transfer, and protocol-based 2D-to-3D material updating**

</div>

---

## At a Glance

This repository is a **public research release** derived from the thesis workflow. It preserves the main computational stages of the method while excluding project-specific Unreal Engine assets and other non-redistributable materials.

The public release focuses on:

- batik-aware lightweight generation,
- dual-reference transfer,
- protocol-based 2D-to-3D material updating,
- thesis-style end-to-end performance analysis.

Included:

- Python orchestration and MCP service scripts
- A public-safe Unreal Engine listener template
- A Flux text-to-image workflow
- A dual-reference garment transfer workflow
- Analysis scripts and setup documentation

Excluded:

- The original Unreal Engine project package
- Project-side maps, meshes, UI assets, and materials
- Copyright-restricted Unreal Engine assets
- Private datasets and protected full-resolution resources
- Non-redistributable model weights

## Quick Navigation

- [Method Structure](#thesis-aligned-method-structure)
- [Core Pipeline](#core-pipeline)
- [Workflows](#workflow-options)
- [Workflow Options](#workflow-options)
- [Workflow Compatibility Rules](#workflow-compatibility-rules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Performance Experiment Workflow](#performance-experiment-workflow)
- [Public Unreal Engine Scope](#public-unreal-engine-scope)
- [Reproducibility Notes](#reproducibility-notes)
- [License](#license)

## Thesis-Aligned Method Structure

According to the thesis, the workflow is organised as a chained visual-computing pipeline:

| Stage | Thesis role | Public repository interpretation |
| --- | --- | --- |
| Stage 1 | Batik-aware lightweight generation | Prompt-driven batik pattern generation with lightweight adaptation assumptions |
| Stage 2 | Role-separated multi-reference transfer | Dual-reference transfer with style priors and carrier-structure priors |
| Stage 3 | Protocol-based 2D-to-3D material updating | Generated image forwarded to Unreal Engine and applied as a runtime material update |

## Core Pipeline

The public repository implements the following simplified closed loop:

`User Input -> Orchestrator -> MCP SSE Service -> ComfyUI Workflow -> Bridge -> UE Listener -> UE Main Thread Material Update -> Final Display`

### Main components

| Component | File | Responsibility |
| --- | --- | --- |
| Orchestrator | `src/orchestrator/orchestrator.py` | Receives trigger requests, creates `run_id` / `prompt_id`, coordinates the chain |
| Generation service | `src/sdxl_service/sse_server.py` | Loads the selected workflow, injects prompt and seed, submits to ComfyUI |
| Bridge | `src/ue_bridge/bridge_server.py` | Forwards the generated image path to Unreal Engine |
| UE listener | `src/ue_listener/ue_listener.py` | Public minimal Unreal Engine listener template for texture import and material update |
| Analysis | `analysis/` | Batch trigger, log merge, and thesis-style performance analysis |

## Repository Layout

```text
src/           core orchestration, generation, bridge, and UE listener code
workflows/     public ComfyUI workflow examples
analysis/      batch trigger, merge, and performance analysis scripts
configs/       path, port, and UE material configuration examples
docs/          setup and experiment documentation
examples/      sample prompt payloads
```

## Workflow Options

This repository includes two public workflow examples derived from the thesis context:

| Workflow | File | Intended use | Public release status |
| --- | --- | --- | --- |
| Flux text-to-image | `workflows/batik_workflow_api_1.json` | Batik-oriented prompt generation | Default public workflow |
| Dual-reference garment transfer | `workflows/batik_garment_transfer_dual_reference.json` | Product-level transfer experiments | Optional advanced workflow |

By default, `configs/paths.example.json` points to the text-to-image workflow for easier public reproduction.

## Workflow Compatibility Rules

The current public `src/sdxl_service/sse_server.py` applies a lightweight workflow adaptation strategy before submission to ComfyUI.

### Default supported node injection rules

| Injection target | Priority | Expected node | Action |
| --- | --- | --- | --- |
| Prompt | 1 | `WeiLinComfyUIPromptToLoras` | Writes `positive` and `negative` |
| Prompt | 2 | `CLIPTextEncode` | Writes `text = positive` |
| Prompt | Fallback | `CLIPTextEncodeFlux` | Writes positive prompt into `clip_l` and `t5xxl` if present |
| Seed | 1 | `RandomNoise` | Writes `noise_seed` |
| Seed | Fallback | `KSampler` | Writes `seed` |
| Output | Reuse | `SaveImage` | Uses existing save node if present |
| Output | Inject | `PreviewImage` trace | Injects a `SaveImage` node when possible |

### Practical implications

- The default Flux text-to-image workflow is the safest public workflow
- The dual-reference workflow may still work if it exposes compatible prompt and output nodes
- Custom workflows with different prompt or output conventions may require manual adaptation in `sse_server.py`

## Public Unreal Engine Scope

This repository intentionally ships only a **minimal public Unreal Engine reproduction path**.

### Included on the UE side

- A public-safe demo material instance naming convention
- A public-safe texture parameter naming convention
- A minimal Python listener
- A documented 2D-to-3D texture update path

### Excluded from the UE side

- The original thesis project package
- Original maps, meshes, UI assets, and scene layout
- Copyright-restricted assets
- Project-specific material assets used in the closed internal environment

## Quick Start

### Step 1. Prepare the environment

Read these first:

- `docs/setup/environment.md`
- `docs/setup/comfyui_setup.md`
- `docs/setup/ue_setup.md`

### Step 2. Start the services

Recommended startup order:

1. Start ComfyUI
2. Start `src/sdxl_service/sse_server.py`
3. Start `src/ue_bridge/bridge_server.py`
4. Run `src/ue_listener/ue_listener.py` inside Unreal Engine
5. Start `src/orchestrator/orchestrator.py`

### Step 3. Trigger one run

Send a POST request to:

```text
http://127.0.0.1:3002/generate_then_update
```

If the environment is correctly configured, the generated batik image should be produced by ComfyUI and then imported into Unreal Engine as a texture update on your own demo material.

## Configuration

The public release follows this priority order:

1. Environment variables
2. Local config files in `configs/*.json`
3. Repository-relative defaults

### Adjust at least

- Log directory
- ComfyUI output directory
- Workflow path
- Orchestrator trigger port
- MCP SSE port
- Bridge port
- UE listener port
- Unreal material instance and texture parameter names

## Performance Experiment Workflow

This repository includes a minimal thesis-oriented runtime evaluation toolchain:

| Script | Role |
| --- | --- |
| `analysis/run_performance_batch.py` | Sequential trigger script |
| `analysis/merge_logs.py` | Merges four-stage JSONL logs |
| `analysis/analyze_performance.py` | Computes end-to-end response metrics |

### Main timing metrics

- `T1`: orchestration dispatch delay
- `T2`: generation service pre-inference delay
- `T3`: model inference time
- `T4`: generation-to-UE transfer delay
- `T5`: UE display update delay
- `T_total`: full end-to-end response time

## Reproducibility Notes

For successful reproduction, make sure:

- The selected workflow matches your installed ComfyUI nodes
- The dual-reference workflow is used only when the reference images and related nodes are locally available
- The Unreal Engine demo material and texture parameter exist
- The UE listener is running inside Unreal Engine
- All service ports are consistent

## Citation

If you use this repository in academic work, please cite the corresponding thesis, paper, or repository release after publication.

```bibtex
@misc{lightweight_multireference_batik_workflow,
  title={Lightweight Multi-Reference Generative Workflow for Batik Pattern Transfer and Immersive Cultural Heritage Visualisation},
  author={Your Name},
  year={2026},
  howpublished={GitHub repository}
}
```

## License

This repository uses the MIT License for the public code release.

Please separately verify the licenses of:

- Unreal Engine
- ComfyUI and custom nodes
- FLUX-related model weights
- LoRA weights
- Any locally prepared reference images or datasets
