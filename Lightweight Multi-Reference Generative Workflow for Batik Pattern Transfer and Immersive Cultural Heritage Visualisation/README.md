# Lightweight Multi-Reference Generative Workflow for Batik Pattern Transfer and Immersive Cultural Heritage Visualisation

A research-oriented MCP-based AIGC pipeline for batik image generation, Unreal Engine material auto-update, and end-to-end performance analysis.

## Overview

This repository contains the core scripts and experiment utilities for a lightweight closed-loop workflow that connects:

1. user prompt input and trigger request,
2. an MCP-based orchestration layer,
3. ComfyUI / Flux-based image generation and transfer,
4. bridge-based result forwarding,
5. Unreal Engine texture import and material replacement,
6. end-to-end performance logging and analysis.

The project is intended for:

- research prototype release,
- thesis experiment reproduction,
- MCP orchestration reference,
- Unreal Engine automatic material texture replacement workflows.

## Core Pipeline

The main system flow is:

`User Input -> Orchestrator -> MCP SSE Service -> ComfyUI / SDXL -> Bridge -> UE Listener -> UE Main Thread Material Update -> Final Display`

In the current implementation:

- `src/orchestrator/orchestrator.py` receives trigger requests and coordinates the closed loop.
- `src/sdxl_service/sse_server.py` submits the selected ComfyUI workflow to ComfyUI and returns the generated image path.
- `src/ue_bridge/bridge_server.py` forwards the generated image path to Unreal Engine.
- `src/ue_listener/ue_listener.py` is a minimal public Unreal Engine listener template for texture import and material parameter update.
- `analysis/` contains scripts for batch triggering, log merging, and performance analysis.

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
|  `- batik_garment_transfer_dual_reference.json
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

## Features

- MCP-based multi-service orchestration.
- ComfyUI workflow-based image generation and transfer.
- Unreal Engine texture auto-import and material parameter replacement.
- Closed-loop visualization from prompt to final display.
- End-to-end performance logging across orchestration, generation, bridge, and UE display stages.
- Batch triggering utilities for thesis-oriented system performance experiments.
- Log merge and performance analysis scripts.

## Public Release Note

This public repository does **not** include the original Unreal Engine project assets, copyrighted scene setup, or private production-side UE content from the research environment.

Instead, it provides:

- a simplified public UE listener template,
- a minimal reproducible UE setup guide,
- generic asset naming examples,
- the Python-side orchestration and analysis pipeline.

If you want to reproduce the UE workflow, create your own minimal UE project and follow the setup instructions in `docs/setup/ue_setup.md`.

## Workflow Options

This repository currently includes two public ComfyUI workflow examples:

- `workflows/batik_workflow_api_1.json`
  - a Flux text-to-image workflow
  - suitable as the default public demo workflow
  - requires only prompt input and seed
- `workflows/batik_garment_transfer_dual_reference.json`
  - a dual-reference garment transfer workflow
  - intended for clothing / carrier image transfer experiments
  - requires additional reference images and compatible custom nodes in ComfyUI

By default, `configs/paths.example.json` keeps `workflow_path` pointed to the text-to-image workflow for easier public reproduction.

If you want to switch to the dual-reference workflow, update:

```json
"workflow_path": "workflows/batik_garment_transfer_dual_reference.json"
```

before starting `src/sdxl_service/sse_server.py`.

### Workflow Compatibility Rules

The current public `src/sdxl_service/sse_server.py` applies a lightweight workflow adaptation strategy before submitting the graph to ComfyUI.

Default supported node injection rules are:

- **Prompt injection priority**
  - `WeiLinComfyUIPromptToLoras`
    - writes `positive` and `negative`
  - `CLIPTextEncode`
    - writes `text = positive`
    - does not automatically map a separate negative prompt branch
  - fallback: `CLIPTextEncodeFlux`
    - writes the positive prompt into `clip_l` and `t5xxl` when these inputs exist

- **Seed injection priority**
  - `RandomNoise`
    - writes `noise_seed`
  - fallback: `KSampler`
    - writes `seed`

- **Output image handling**
  - if a `SaveImage` node already exists, it is reused
  - if no `SaveImage` node exists, the service tries to inject one
  - current injection strategy traces image output from `PreviewImage -> images`
  - injected `SaveImage` uses the filename prefix `MCP_Batik`

Practical implications:

- the default text-to-image workflow is fully compatible with the current adapter logic
- the dual-reference garment transfer workflow may run, but prompt adaptation depends on whether the workflow still exposes a supported text node
- if your workflow uses custom prompt nodes outside the rules above, you should extend `sse_server.py` accordingly
- if your workflow has no `PreviewImage` and no `SaveImage`, automatic output capture may fail

## UE-Side Material Update Workflow

Inside Unreal Engine, the automatic texture replacement process is completed through the following steps:

1. Run `ue_listener.py` inside the UE Python environment.
2. Start a local HTTP listener on the configured port.
3. Receive `/update_texture` requests from the bridge service.
4. Push the update task into the UE-safe task queue.
5. Execute the import and material update in the UE main thread.
6. Import the external generated image as a UE texture asset.
7. Locate the target material instance.
8. Replace the configured texture parameter.
9. Redraw the viewport so the new result is visible immediately.

Current default assumptions in the public template:

- material instance name: `MI_PublicDemo_Display`
- texture parameter name: `GeneratedTexture`
- import destination: `/Game/Generated`

## Quick Start

### 1. Prepare the environment

Read the setup docs first:

- `docs/setup/environment.md`
- `docs/setup/comfyui_setup.md`
- `docs/setup/ue_setup.md`

### 2. Start the services

Recommended startup order:

1. Start ComfyUI.
2. Start `src/sdxl_service/sse_server.py`.
3. Start `src/ue_bridge/bridge_server.py`.
4. Run `src/ue_listener/ue_listener.py` inside Unreal Engine.
5. Start `src/orchestrator/orchestrator.py`.

### 3. Trigger a single run

Send a POST request to:

```text
http://127.0.0.1:3002/generate_then_update
```

If the pipeline is correctly configured, the generated batik texture should be imported into Unreal Engine and applied to your own demo material instance.

## Performance Experiment Workflow

This repository includes utilities for thesis Section 4.4 style performance experiments.

### Batch trigger

```bash
python analysis/run_performance_batch.py
```

### Merge logs

```bash
python analysis/merge_logs.py
```

### Analyze performance

```bash
python analysis/analyze_performance.py
```

See `docs/experiments/performance.md` for the full workflow.

## Environment Requirements

Recommended environment:

- Windows
- Python 3.10+
- Unreal Engine 5 with Python enabled
- ComfyUI installed and running locally
- MCP-compatible Python environment

## Configuration

Before running the system, adjust the local paths and ports through configuration rather than editing source code directly.

The public release now follows this priority order:

1. environment variables,
2. local config files in `configs/*.json`,
3. repository-relative defaults.

You should adapt at least:

- log output directory,
- ComfyUI output directory,
- workflow path,
- UE listener port,
- bridge port,
- orchestrator trigger port,
- UE material instance and texture parameter names.

## Reproducibility Notes

For successful reproduction, make sure:

- ComfyUI output path matches the path used by the scripts.
- the Unreal Engine project contains your own public demo material instance and texture parameter.
- the UE listener is actually running inside the Unreal Engine editor.
- all ports are consistent across the four stages.
- the workflow JSON matches your installed ComfyUI nodes.
- if you use the dual-reference workflow, the required reference images and custom nodes are available in your local ComfyUI environment.

## Current Limitations

This repository is a research-oriented prototype rather than a fully productized software package.

Known limitations include:

- dependence on local Windows paths,
- a minimal public UE template rather than the original project-side UE assets,
- environment-specific ComfyUI workflow dependencies,
- no fully externalized configuration layer,
- reliance on Unreal Engine editor-side Python execution.

## Recommended Open-Source Scope

Recommended for public release:

- orchestration scripts,
- MCP service scripts,
- a simplified UE listener template,
- workflow examples for both text-to-image and dual-reference transfer,
- analysis scripts,
- setup documentation.

Not recommended for direct public release without review:

- large local datasets,
- generated logs,
- generated CSV outputs,
- cached Unreal Engine folders,
- private assets or model weights,
- unpublished thesis materials.

## Citation

If you use this project in academic work, please cite the corresponding thesis, paper, or repository release after publication.

```bibtex
@misc{mcp_batik_ue,
  title={Lightweight Multi-Reference Generative Workflow for Batik Pattern Transfer and Immersive Cultural Heritage Visualisation},
  author={Your Name},
  year={2026},
  howpublished={GitHub repository}
}
```

## License

This repository is released under the MIT License. Please separately verify the licenses of:

- Unreal Engine,
- ComfyUI,
- model weights,
- custom nodes,
- external assets,
- datasets.

## Acknowledgements

This project builds upon:

- Unreal Engine,
- ComfyUI,
- SDXL-based image generation workflows,
- MCP-based service orchestration.
