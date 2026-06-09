import unreal
import json
import logging
import threading
import queue
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime, timezone

# Public minimal UE listener template.
# This file is a simplified reproducible example for open-source release.
# It intentionally avoids shipping the original project assets or private UE setup.

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import (
    get_comfyui_output_dir,
    get_comfyui_temp_dir,
    get_import_destination_path,
    get_import_texture_asset_name,
    get_log_dir,
    get_material_instance_name,
    get_port,
    get_texture_param_names,
)

PORT = get_port("ue_listener_port", 5000)
MATERIAL_INSTANCE_NAME = get_material_instance_name("MI_PublicDemo_Display")
TEXTURE_PARAM_NAMES = get_texture_param_names(["GeneratedTexture"])
COMFYUI_DIRS = [str(path) for path in (get_comfyui_output_dir(), get_comfyui_temp_dir()) if path]
IMPORT_DESTINATION_PATH = get_import_destination_path("/Game/Generated")
IMPORT_TEXTURE_NAME = get_import_texture_asset_name("T_Generated_Dynamic")
LOG_DIR = str(get_log_dir())
UE_LOG_PATH = os.path.join(LOG_DIR, "ue_listener_log.jsonl")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UEPublicListener")
task_queue = queue.Queue()


def iso_utc_ms_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def append_jsonl(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as exc:
        try:
            logger.error(f"Failed to write log: {exc}")
        except Exception:
            pass


def texture_asset_path():
    return f"{IMPORT_DESTINATION_PATH}/{IMPORT_TEXTURE_NAME}"


def process_tasks(delta_time):
    try:
        while not task_queue.empty():
            task = task_queue.get_nowait()
            task()
    except Exception as exc:
        logger.error(f"Task processing failed: {exc}")


try:
    unreal.unregister_slate_post_tick_callback(process_tasks)
except Exception:
    pass
unreal.register_slate_post_tick_callback(process_tasks)
logger.info("Registered Slate Post-Tick callback")


def find_asset(name, class_name="MaterialInstanceConstant"):
    asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
    asset_filter = unreal.ARFilter(
        class_names=[class_name],
        recursive_paths=True,
        package_paths=["/Game"],
    )
    for asset_data in asset_registry.get_assets(asset_filter):
        if asset_data.asset_name == name:
            return asset_data.get_asset()
    return None


def find_latest_image_path():
    candidates = []
    for directory in COMFYUI_DIRS:
        if not os.path.isdir(directory):
            continue
        try:
            for file_name in os.listdir(directory):
                lower_name = file_name.lower()
                if lower_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
                    full_path = os.path.join(directory, file_name)
                    try:
                        candidates.append((os.path.getmtime(full_path), full_path))
                    except Exception:
                        pass
        except Exception:
            pass
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def log_failure(run_id, prompt_id, recv_time, image_path, message):
    append_jsonl(UE_LOG_PATH, {
        "module": "ue_listener",
        "run_id": run_id,
        "prompt_id": prompt_id,
        "recv_time": recv_time,
        "update_done_time": None,
        "success": False,
        "error_type": "E3",
        "error_message": message,
        "image_path": image_path,
    })


def update_texture_logic(image_path, run_id=None, prompt_id=None, recv_time=None):
    logger.info(f"Start processing image on the game thread: {image_path}")

    if not os.path.exists(image_path):
        logger.error(f"File not found: {image_path}")
        log_failure(run_id, prompt_id, recv_time, image_path, "file not found")
        return

    task = unreal.AssetImportTask()
    task.filename = image_path
    task.destination_path = IMPORT_DESTINATION_PATH
    task.destination_name = IMPORT_TEXTURE_NAME
    task.replace_existing = True
    task.automated = True
    task.save = True
    task.factory = unreal.TextureFactory()

    logger.info("Importing texture asset...")
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    imported_assets = task.get_objects()
    texture_asset = imported_assets[0] if imported_assets else None
    if not texture_asset:
        texture_asset = unreal.load_asset(texture_asset_path())

    if not texture_asset:
        logger.error("Texture import failed")
        log_failure(run_id, prompt_id, recv_time, image_path, "texture import failed")
        return

    texture_asset.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    texture_asset.set_editor_property("srgb", True)

    material_asset = find_asset(MATERIAL_INSTANCE_NAME)
    if not material_asset:
        material_asset = unreal.load_asset(f"/Game/{MATERIAL_INSTANCE_NAME}")
    if not material_asset:
        material_asset = unreal.load_asset(f"/Game/Materials/{MATERIAL_INSTANCE_NAME}")
    if not material_asset:
        material_asset = find_asset(MATERIAL_INSTANCE_NAME, "Material")

    if not material_asset:
        logger.error(f"Material asset not found: {MATERIAL_INSTANCE_NAME}")
        log_failure(run_id, prompt_id, recv_time, image_path, "material not found")
        return

    updated_any = False
    if isinstance(material_asset, unreal.MaterialInstanceConstant):
        for param_name in TEXTURE_PARAM_NAMES:
            try:
                unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
                    material_asset, param_name, texture_asset
                )
                updated_any = True
            except Exception:
                pass
        if updated_any:
            unreal.MaterialEditingLibrary.update_material_instance(material_asset)
    elif isinstance(material_asset, unreal.Material):
        for param_name in TEXTURE_PARAM_NAMES:
            try:
                unreal.MaterialEditingLibrary.set_material_texture_parameter_value(
                    material_asset, param_name, texture_asset
                )
                updated_any = True
            except Exception:
                pass

    if not updated_any:
        logger.error("No texture parameter was updated")
        log_failure(run_id, prompt_id, recv_time, image_path, "no parameter updated")
        return

    try:
        unreal.EditorAssetLibrary.save_asset(material_asset.get_path_name())
    except Exception:
        pass

    try:
        unreal.EditorLevelLibrary.redraw_all_viewports()
    except Exception:
        pass

    update_done_time = iso_utc_ms_now()
    append_jsonl(UE_LOG_PATH, {
        "module": "ue_listener",
        "run_id": run_id,
        "prompt_id": prompt_id,
        "recv_time": recv_time,
        "update_done_time": update_done_time,
        "success": True,
        "image_path": image_path,
        "material_name": material_asset.get_name(),
    })
    logger.info(f"Material updated successfully: {material_asset.get_name()}")


class SimpleUEHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/update_texture":
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
                post_data = self.rfile.read(content_length) if content_length else b""
                data = json.loads(post_data.decode("utf-8")) if post_data else {}
                image_path = data.get("image_path")
                run_id = data.get("run_id")
                prompt_id = data.get("prompt_id")
                recv_time = iso_utc_ms_now()

                if image_path:
                    task_queue.put(
                        lambda ip=image_path, ri=run_id, pi=prompt_id, rt=recv_time: update_texture_logic(ip, ri, pi, rt)
                    )
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK - Task Queued")
                else:
                    log_failure(run_id, prompt_id, recv_time, image_path, "missing image_path")
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing image_path")
            except Exception as exc:
                recv_time = iso_utc_ms_now()
                log_failure(None, None, recv_time, None, str(exc))
                logger.error(f"HTTP error: {exc}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(exc).encode("utf-8"))
        elif self.path == "/trigger_latest":
            try:
                latest = find_latest_image_path()
                if latest:
                    task_queue.put(lambda path=latest: update_texture_logic(path))
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK - Latest Queued")
                else:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(b"No images found")
            except Exception as exc:
                logger.error(f"Trigger error: {exc}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(exc).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def run_server():
    server_address = ("0.0.0.0", PORT)
    try:
        httpd = HTTPServer(server_address, SimpleUEHandler)
        logger.info(f"Public UE listener started on port {PORT}")
        httpd.serve_forever()
    except OSError as exc:
        logger.error(f"Port {PORT} may already be in use: {exc}")
    except Exception as exc:
        logger.error(f"Server error: {exc}")


if __name__ == "__main__":
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    logger.info("Background UE listener thread started")
