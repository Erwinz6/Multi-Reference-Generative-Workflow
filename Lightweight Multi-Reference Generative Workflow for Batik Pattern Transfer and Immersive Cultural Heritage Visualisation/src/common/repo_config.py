import json
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs"


def _load_json_config(stem):
    for candidate in (CONFIG_DIR / f"{stem}.json", CONFIG_DIR / f"{stem}.example.json"):
        if candidate.is_file():
            try:
                with open(candidate, "r", encoding="utf-8") as handle:
                    return json.load(handle)
            except Exception:
                return {}
    return {}


PATHS_CONFIG = _load_json_config("paths")
PORTS_CONFIG = _load_json_config("ports")
UE_CONFIG = _load_json_config("ue_material")


def repo_root():
    return REPO_ROOT


def resolve_repo_path(value, fallback_relative=None):
    raw_value = value if value not in (None, "") else fallback_relative
    if raw_value in (None, ""):
        return None
    path = Path(raw_value).expanduser()
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def get_path_config(key, fallback_relative=None, env_name=None):
    if env_name:
        env_value = os.environ.get(env_name)
        if env_value:
            return resolve_repo_path(env_value)
    return resolve_repo_path(PATHS_CONFIG.get(key), fallback_relative)


def get_log_dir():
    return get_path_config("log_dir", "logs", "MCP_BATIK_LOG_DIR")


def get_workflow_path(default_relative="workflows/batik_workflow_api_1.json"):
    return get_path_config("workflow_path", default_relative, "MCP_WORKFLOW_PATH")


def get_comfyui_output_dir():
    return get_path_config("comfyui_output_dir", "../ComfyUI/output", "COMFYUI_OUTPUT_DIR")


def get_comfyui_temp_dir():
    return get_path_config("comfyui_temp_dir", "../ComfyUI/temp", "COMFYUI_TEMP_DIR")


def get_port(key, default):
    env_name = f"MCP_{key.upper()}"
    env_value = os.environ.get(env_name)
    if env_value:
        try:
            return int(env_value)
        except ValueError:
            pass
    value = PORTS_CONFIG.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_host(env_name, default):
    return os.environ.get(env_name, default)


def build_local_url(port_key, default_port, path="", host_env="MCP_LOCAL_HOST", default_host="127.0.0.1", url_env=None):
    if url_env:
        env_url = os.environ.get(url_env)
        if env_url:
            return env_url
    host = get_host(host_env, default_host)
    port = get_port(port_key, default_port)
    return f"http://{host}:{port}{path}"


def get_import_destination_path(default="/Game/Generated"):
    return os.environ.get("UE_IMPORT_DESTINATION_PATH") or PATHS_CONFIG.get("ue_import_path", default)


def get_material_instance_name(default="MI_PublicDemo_Display"):
    return os.environ.get("UE_MATERIAL_INSTANCE_NAME") or UE_CONFIG.get("material_instance_name", default)


def get_texture_param_names(default=None):
    if default is None:
        default = ["GeneratedTexture"]
    env_value = os.environ.get("UE_TEXTURE_PARAM_NAMES")
    if env_value:
        values = [item.strip() for item in env_value.split(",") if item.strip()]
        if values:
            return values
    values = UE_CONFIG.get("texture_parameter_names", default)
    if isinstance(values, list):
        return values
    return list(default)


def get_import_texture_asset_name(default="T_Generated_Dynamic"):
    return os.environ.get("UE_IMPORT_TEXTURE_NAME") or UE_CONFIG.get("import_texture_asset_name", default)
