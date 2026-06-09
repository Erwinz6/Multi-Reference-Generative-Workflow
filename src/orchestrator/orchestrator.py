import asyncio
import random
import logging
import time
import threading
import json
import queue
import os
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from contextlib import AsyncExitStack

# 引入 MCP 客户端库
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import build_local_url, get_log_dir, get_port

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Orchestrator")

AUTO_RUN = False
TRIGGER_PORT = get_port("orchestrator_trigger_port", 3002)

POSITIVE_PROMPT = """Traditional Miao batik art masterpiece, top-down view. A magnificent white mandala design centered on a deep indigo blue fabric background. The mandala resembles a glowing sun with intricate light radiating outward to form a perfect circular pattern. Surrounding the center are exquisite motifs of swimming fish and flying birds, arranged in a strictly symmetrical composition, overlapping with blooming flowers and lush leaves. The texture features realistic wax resist dyeing effects with rich \"ice crackle\" details (binglie wen). High contrast, 8k resolution, macro photography, extremely detailed fabric grain, cultural heritage aesthetic."""
NEGATIVE_PROMPT = """blur, low quality, distortion, asymmetry, messy lines, watermark, text, signature, washed out colors, deformed fish, deformed birds."""

LOG_DIR = str(get_log_dir())
ORC_LOG_PATH = os.path.join(LOG_DIR, "orchestrator_log.jsonl")

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

def start_trigger_server(loop, event, q, port=TRIGGER_PORT):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == '/generate_then_update':
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(length) if length>0 else b'{}'
                    data = json.loads(body.decode('utf-8'))
                except Exception:
                    data = {}
                q.put({'positive': data.get('positive'), 'negative': data.get('negative'), 'seed': data.get('seed')})
                loop.call_soon_threadsafe(event.set)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(404)
                self.end_headers()
    threading.Thread(target=lambda: HTTPServer(('0.0.0.0', port), Handler).serve_forever(), daemon=True).start()
    logger.info(f"🕹️ 手动触发服务器启动 @ {build_local_url('orchestrator_trigger_port', port, '/generate_then_update', url_env='MCP_ORCHESTRATOR_TRIGGER_URL')}")

async def run_orchestrator():
    # MCP 服务器地址
    comfyui_url = build_local_url("sdxl_sse_port", 8000, "/sse", url_env="MCP_SDXL_SSE_URL")
    ue5_url = build_local_url("ue_bridge_port", 8001, "/sse", url_env="MCP_UE_BRIDGE_URL")
    
    logger.info("🚀 正在启动 AIGC 闭环系统编排器 (稳定版)...")
    
    prompts = [
        "traditional batik pattern, wax resist dyeing, indigo blue and white, intricate geometric floral motifs, cracked wax texture, high quality, 4k texture",
        "modern batik art, vibrant colors, abstract shapes, fluid lines, cultural fusion, detailed fabric texture",
        "ancient dragon batik, mythical creature, swirling clouds, deep red and gold, ceremonial cloth style"
    ]
    cycle_count = 0

    # 外层循环：负责连接管理和重连
    while True:
        try:
            # 使用 AsyncExitStack 优雅地管理多个异步上下文连接
            async with AsyncExitStack() as stack:
                logger.info(f"🔌 正在建立连接...")
                
                # 连接 ComfyUI MCP
                try:
                    comfy_read, comfy_write = await stack.enter_async_context(sse_client(url=comfyui_url))
                    comfy_session = await stack.enter_async_context(ClientSession(comfy_read, comfy_write))
                    await comfy_session.initialize()
                    logger.info("✅ ComfyUI MCP 连接成功")
                except Exception as e:
                    logger.error(f"❌ 无法连接 ComfyUI MCP ({comfyui_url}): {e}")
                    raise e # 抛出异常触发重连

                # 连接 UE5 MCP
                try:
                    ue5_read, ue5_write = await stack.enter_async_context(sse_client(url=ue5_url))
                    ue5_session = await stack.enter_async_context(ClientSession(ue5_read, ue5_write))
                    await ue5_session.initialize()
                    logger.info("✅ UE5 MCP 连接成功")
                except Exception as e:
                    logger.error(f"❌ 无法连接 UE5 MCP ({ue5_url}): {e}")
                    raise e # 抛出异常触发重连

                # 启动手动触发支持
                loop = asyncio.get_running_loop()
                manual_event = asyncio.Event()
                manual_queue = queue.Queue()
                start_trigger_server(loop, manual_event, manual_queue)
                logger.info("🎉 系统就绪：支持手动触发。按 UE 的数字键盘 1 或调用 /generate_then_update 即可。")
                
                # 内层循环：负责业务逻辑
                while True:
                    if not AUTO_RUN:
                        logger.info("⌨️ 等待手动触发...")
                        await manual_event.wait()
                        manual_event.clear()

                    processed = 0
                    while True:
                        try:
                            req = manual_queue.get_nowait()
                        except Exception:
                            if processed == 0:
                                req = {}
                            else:
                                break
                        processed += 1

                        cycle_count += 1
                        logger.info(f"\n--- 第 {cycle_count} 轮执行开始 ---")
                        run_id = str(uuid.uuid4())
                        prompt_id = str(uuid.uuid4())
                        trigger_time = iso_utc_ms_now()
                        
                        positive = (req.get("positive") or POSITIVE_PROMPT)
                        negative = (req.get("negative") or NEGATIVE_PROMPT)
                        seed = (req.get("seed") or random.randint(1, 999999999))
                        
                        logger.info(f"📋 [指令] Positive: {positive[:50]}...")
                        logger.info(f"🧹 [指令] Negative: {negative[:50]}...")
                        logger.info(f"🎨 [生成] 调用 ComfyUI 生图... (Seed: {seed})")
                        start_time = time.time()
                        
                        try:
                            request_sent_time = iso_utc_ms_now()
                            result = await asyncio.wait_for(
                                comfy_session.call_tool("generate_batik", arguments={"positive": positive, "negative": negative, "seed": seed, "run_id": run_id, "prompt_id": prompt_id}),
                                timeout=320
                            )
                            
                            image_path = ""
                            if result.content and hasattr(result.content[0], 'text'):
                                image_path = result.content[0].text.strip()
                            
                            if not image_path or "失败" in image_path or "Error" in image_path or "超时" in image_path:
                                logger.error(f"❌ 生成失败: {image_path}")
                                append_jsonl(ORC_LOG_PATH, {
                                    "module": "orchestrator",
                                    "run_id": run_id,
                                    "prompt_id": prompt_id,
                                    "trigger_time": trigger_time,
                                    "request_sent_time": request_sent_time,
                                    "success": False,
                                    "error_type": "E1",
                                    "error_message": str(image_path),
                                    "image_path": image_path
                                })
                            else:
                                elapsed = time.time() - start_time
                                logger.info(f"✅ [生成] 成功! 耗时 {elapsed:.1f}s")
                                logger.info(f"📂 图片路径: {image_path}")

                                logger.info(f"📺 [显示] 发送至 UE5 更新材质...")
                                ue_result = await asyncio.wait_for(
                                    ue5_session.call_tool("update_vr_display", arguments={"image_path": image_path, "run_id": run_id, "prompt_id": prompt_id}),
                                    timeout=20
                                )
                                
                                ue_msg = ""
                                if ue_result.content and hasattr(ue_result.content[0], 'text'):
                                    ue_msg = ue_result.content[0].text
                                logger.info(f"📥 [UE5反馈] {ue_msg}")
                                append_jsonl(ORC_LOG_PATH, {
                                    "module": "orchestrator",
                                    "run_id": run_id,
                                    "prompt_id": prompt_id,
                                    "trigger_time": trigger_time,
                                    "request_sent_time": request_sent_time,
                                    "success": True,
                                    "error_type": None,
                                    "error_message": None,
                                    "image_path": image_path,
                                    "ue_feedback_text": ue_msg,
                                })
                            
                        except asyncio.TimeoutError:
                            logger.error("❌ 操作超时")
                            append_jsonl(ORC_LOG_PATH, {
                                "module": "orchestrator",
                                "run_id": run_id if 'run_id' in locals() else None,
                                "prompt_id": prompt_id if 'prompt_id' in locals() else None,
                                "trigger_time": trigger_time if 'trigger_time' in locals() else None,
                                "request_sent_time": request_sent_time if 'request_sent_time' in locals() else None,
                                "success": False,
                                "error_type": "E4",
                                "error_message": "Timeout",
                                "image_path": None
                            })
                        except Exception as tool_err:
                            logger.error(f"❌ 业务逻辑异常: {tool_err}")
                            append_jsonl(ORC_LOG_PATH, {
                                "module": "orchestrator",
                                "run_id": run_id if 'run_id' in locals() else None,
                                "prompt_id": prompt_id if 'prompt_id' in locals() else None,
                                "trigger_time": trigger_time if 'trigger_time' in locals() else None,
                                "request_sent_time": request_sent_time if 'request_sent_time' in locals() else None,
                                "success": False,
                                "error_type": "E1",
                                "error_message": str(tool_err),
                                "image_path": None
                            })
                            if "connection" in str(tool_err).lower() or "closed" in str(tool_err).lower():
                                raise tool_err

                        if AUTO_RUN:
                            logger.info("⏳ 本轮结束，等待 10 秒...")
                            await asyncio.sleep(10)

        except KeyboardInterrupt:
            logger.info("\n🛑 用户手动停止 Orchestrator")
            break
        except Exception as e:
            logger.warning(f"⚠️ 连接中断或发生错误: {e}")
            logger.info("🔄 5 秒后尝试重连...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # 运行异步主程序
    asyncio.run(run_orchestrator())
