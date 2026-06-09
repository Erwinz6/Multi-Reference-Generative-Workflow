<div align="center">

# Lightweight Multi-Reference Generative Workflow for Batik Pattern Transfer and Immersive Cultural Heritage Visualisation

**A thesis-aligned public release for batik-aware lightweight generation, dual-reference transfer, and protocol-based 2D-to-3D material updating**

</div>

---

## At a Glance

This repository is a **public research release** derived from the thesis workflow. It keeps the computational structure of the method while removing project-specific Unreal Engine assets and other non-redistributable materials.

The repository is organised around the three connected stages described in the thesis:

1. **Batik-aware lightweight generative adaptation**
2. **Role-separated multi-reference transfer**
3. **Protocol-based 2D-to-3D material updating**

### Included in this release

- Python orchestration and MCP service scripts
- A public-safe Unreal Engine listener template
- A Flux text-to-image workflow
- A dual-reference garment transfer workflow
- Performance experiment scripts for thesis-style runtime analysis
- Configuration examples and setup documentation

### Not included in this release

- The original Unreal Engine project package
- Project-side maps, meshes, UI assets, and materials
- Copyrighted Unreal Engine scene assets
- Private datasets or protected full-resolution resources
- Model weights that are not suitable for redistribution

## Quick Navigation

- [Method Structure](#thesis-aligned-method-structure)
- [Core Pipeline](#core-pipeline)
- [Repository Structure](#repository-structure)
- [Workflow Options](#workflow-options)
- [Workflow Compatibility Rules](#workflow-compatibility-rules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Performance Experiment Workflow](#performance-experiment-workflow)
- [Public Unreal Engine Scope](#public-unreal-engine-scope)
- [Reproducibility Notes](#reproducibility-notes)
- [License](#license)

## Thesis-Aligned Method Structure

According to the thesis, the workflow is formalised as a chained visual-computing pipeline:

| Stage | Thesis role | Public repository interpretation |
| --- | --- | --- |
| Stage 1 | Batik-aware lightweight generation | Prompt-driven batik pattern generation with lightweight adaptation assumptions |
| Stage 2 | Role-separated multi-reference transfer | Dual-reference transfer with style priors and carrier-structure priors |
| Stage 3 | Protocol-based 2D-to-3D material updating | Generated image forwarded to Unreal Engine and applied as a runtime material update |

### Stage 1: Batik-aware lightweight generation

- Learns batik-specific stylistic residuals over a frozen diffusion backbone
- Uses lightweight adaptation and quantised inference ideas from the thesis
- Produces a batik pattern candidate from prompt-driven generation

### Stage 2: Role-separated multi-reference transfer

- Uses a batik reference image for style priors
- Uses a carrier image for structural and material priors
- Uses an editing prompt to coordinate preservation constraints and editable attributes

### Stage 3: Protocol-based 2D-to-3D material updating

- Treats the generated result as a texture update event
- Forwards the generated image to Unreal Engine
- Imports it as a texture and updates a target material parameter
- Enables near-real-time visual feedback in a 3D scene

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

## Repository Structure

```text
.
|- README.md
|- NOTICE.md
|- CONTRIBUTING.md
|- RELEASE_CHECKLIST.md
|- LICENSE
|- .gitignore
|- requirements.txt
|- configs/
|  |- paths.example.json
|  |- ports.example.json
|  `- ue_material.example.json
|- docs/
|  |- architecture/
|  |  `- pipeline.md
|  |- setup/
|  |  |- environment.md
|  |  |- comfyui_setup.md
|  |  `- ue_setup.md
|  `- experiments/
|     `- performance.md
|- src/
|  |- common/
|  |  |- __init__.py
|  |  `- repo_config.py
|  |- orchestrator/
|  |  `- orchestrator.py
|  |- sdxl_service/
|  |  `- sse_server.py
|  |- ue_bridge/
|  |  `- bridge_server.py
|  `- ue_listener/
|     `- ue_listener.py
|- workflows/
|  |- batik_workflow_api_1.json
|  |- batik_garment_transfer_dual_reference.json
|  `- README.md
|- analysis/
|  |- merge_logs.py
|  |- analyze_performance.py
|  |- run_performance_batch.py
|  `- README.md
|- examples/
|  `- prompts/
|     `- sample_prompt.json
|- ue_project_template/
|  `- required_assets.md
`- dataset_manifest/
   `- README.md
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

## Recommended Open-Source Scope

### Recommended for public release

- Orchestration scripts
- MCP service scripts
- A simplified public UE listener template
- Text-to-image and dual-reference workflow examples
- Analysis scripts
- Setup documentation

### Not recommended for public release without review

- Large local datasets
- Generated logs
- Generated CSV outputs
- Cached Unreal Engine folders
- Private assets or model weights
- Unpublished thesis materials

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
