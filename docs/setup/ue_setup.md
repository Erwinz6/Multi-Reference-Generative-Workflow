# Unreal Engine Setup

This repository intentionally ships only a minimal public UE reproduction path rather than the original project-specific Unreal assets.

To reproduce the UE-side material update workflow:

1. Create or open a blank Unreal Engine 5 project.
2. Create a new texture-parameterized material or material instance for demonstration.
3. Use a public-safe asset name such as `MI_PublicDemo_Display`.
4. Add a texture parameter such as `GeneratedTexture`.
5. Assign the material instance to a plane, cloth proxy, or any simple display mesh in the scene.
6. Run `src/ue_listener/ue_listener.py` inside the UE Python environment.
7. Confirm the listener starts successfully and the configured port is available.

The public listener imports generated images as textures and replaces the configured material texture parameter on your own demo asset.
