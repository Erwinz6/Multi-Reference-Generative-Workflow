import httpx
from mcp.server.fastmcp import FastMCP
import os, json, logging
import sys
from pathlib import Path
from datetime import datetime, timezone

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import build_local_url, get_log_dir, get_port

mcp = FastMCP("UE5-Bridge-MCP")
mcp.settings.host = "0.0.0.0"
mcp.settings.port = get_port("ue_bridge_port", 8001)

# performance experiment logging: helpers
logger = logging.getLogger("UE5-Bridge-MCP")
LOG_DIR = str(get_log_dir())
BRIDGE_LOG_PATH = os.path.join(LOG_DIR, "bridge_log.jsonl")

def iso_utc_ms_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def append_jsonl(path, obj):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e:
        try:
            logger.error(f"日志写入失败: {e}")
        except Exception:
            pass

@mcp.tool()
async def update_vr_display(image_path: str, run_id: str = None, prompt_id: str = None) -> str:
    """
    通知 Unreal Engine 更新 VR 场景中的显示纹理
    Args:
        image_path: 图片的绝对路径
    """
    ue5_url = build_local_url("ue_listener_port", 5000, "/update_texture", url_env="MCP_UE_LISTENER_URL")
    payload = {"image_path": image_path, "run_id": run_id, "prompt_id": prompt_id}

    try:
        async with httpx.AsyncClient(trust_env=False) as client:
            dispatch_time = iso_utc_ms_now()  # performance experiment logging
            resp = await client.post(ue5_url, json=payload, timeout=15.0)
            return_time = iso_utc_ms_now()  # performance experiment logging
        
        ue_text = (resp.text[:200] if isinstance(resp.text, str) else str(resp.text)[:200])
        if resp.status_code == 200:
            append_jsonl(BRIDGE_LOG_PATH, {
                "module": "bridge",
                "run_id": run_id,
                "prompt_id": prompt_id,
                "dispatch_time": dispatch_time,
                "return_time": return_time,
                "success": True,
                "image_path": image_path,
                "ue_response_text": ue_text
            })  # performance experiment logging
            return f"成功: 已发送图片路径到 UE5 -> {image_path}"
        else:
            append_jsonl(BRIDGE_LOG_PATH, {
                "module": "bridge",
                "run_id": run_id,
                "prompt_id": prompt_id,
                "dispatch_time": dispatch_time,
                "return_time": return_time,
                "success": False,
                "error_type": "E2",
                "error_message": f"HTTP {resp.status_code}",
                "image_path": image_path,
                "ue_response_text": ue_text
            })  # performance experiment logging
            return f"UE5 返回错误: {resp.status_code} - {resp.text}"
            
    except httpx.ConnectError:
        rt = iso_utc_ms_now()
        append_jsonl(BRIDGE_LOG_PATH, {
            "module": "bridge",
            "run_id": run_id,
            "prompt_id": prompt_id,
            "dispatch_time": locals().get("dispatch_time"),
            "return_time": rt,
            "success": False,
            "error_type": "E4",
            "error_message": "connect error",
            "image_path": image_path
        })  # performance experiment logging
        return "无法连接到 UE5，请检查 ue_listener.py 是否运行在端口 5000"
    except Exception as e:
        rt = iso_utc_ms_now()
        append_jsonl(BRIDGE_LOG_PATH, {
            "module": "bridge",
            "run_id": run_id,
            "prompt_id": prompt_id,
            "dispatch_time": locals().get("dispatch_time"),
            "return_time": rt,
            "success": False,
            "error_type": "E2",
            "error_message": str(e),
            "image_path": image_path
        })  # performance experiment logging
        return f"发生异常: {str(e)}"

if __name__ == "__main__":
    print("启动 UE5 Bridge MCP Server @ 0.0.0.0:8001 ...")
    mcp.run(transport="sse")
