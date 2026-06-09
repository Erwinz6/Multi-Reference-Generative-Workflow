import os
import json
import uuid
import random
import logging
import asyncio
import sys
from typing import Optional
from pathlib import Path
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import build_local_url, get_comfyui_output_dir, get_host, get_log_dir, get_port, get_workflow_path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ComfyUI-MCP-SSE")

# performance experiment logging: helpers
LOG_DIR = str(get_log_dir())
SSE_LOG_PATH = os.path.join(LOG_DIR, "sdxl_sse_log.jsonl")

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

# 配置: ComfyUI 输出目录 (根据用户实际环境修改)
COMFYUI_OUTPUT_DIR = str(get_comfyui_output_dir())
# performance experiment logging: timeout bound for polling
TIMEOUT_SECONDS = 300

# 创建 FastMCP 服务
mcp = FastMCP("ComfyUI-MCP-SSE")
# 设置监听地址和端口
mcp.settings.host = "0.0.0.0"
mcp.settings.port = get_port("sdxl_sse_port", 8000)

# Patch: Bypass MCP Host Header check
try:
    from mcp.server import transport_security
    transport_security.validate_host = lambda *args, **kwargs: True
except:
    pass

@mcp.tool()
async def generate_batik(positive: str, negative: Optional[str] = "", seed: Optional[int] = None, run_id: Optional[str] = None, prompt_id: Optional[str] = "performance_prompt_001") -> str:
    """
    生成蜡染风格图片
    Args:
        prompt_text: 提示词文本
        seed: 随机种子 (可选)
    """
    # performance experiment logging
    mcp_receive_time = iso_utc_ms_now()
    infer_start_time = None
    workflow_path = str(get_workflow_path("workflows/batik_workflow_api_1.json"))
    
    if not os.path.exists(workflow_path):
        append_jsonl(SSE_LOG_PATH, {
            "module": "sdxl_sse",
            "run_id": run_id,
            "prompt_id": prompt_id,
            "mcp_receive_time": mcp_receive_time,
            "success": False,
            "error_type": "E1",
            "error_message": f"Missing workflow: {workflow_path}"
        })  # performance experiment logging
        return f"错误: 找不到工作流文件 {workflow_path}"

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except Exception as e:
        append_jsonl(SSE_LOG_PATH, {
            "module": "sdxl_sse",
            "run_id": run_id,
            "prompt_id": prompt_id,
            "mcp_receive_time": mcp_receive_time,
            "success": False,
            "error_type": "E1",
            "error_message": str(e)
        })  # performance experiment logging
        return f"读取工作流文件失败: {str(e)}"

    # ==========================================
    # 1. 修改提示词 (Prompt)
    # ==========================================
    # 适配策略: WeiLinComfyUIPromptToLoras > CLIPTextEncode > CLIPTextEncodeFlux
    prompt_node_id = None
    
    # 优先查找 WeiLinComfyUIPromptToLoras (针对本次工作流)
    for node_id, node in workflow.items():
        if node.get("class_type") == "WeiLinComfyUIPromptToLoras":
            prompt_node_id = node_id
            logger.info(f"找到 WeiLinComfyUIPromptToLoras 节点 ID: {node_id}")
            break
    
    # 如果没找到，找标准 CLIPTextEncode
    if not prompt_node_id:
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                prompt_node_id = node_id
                logger.info(f"找到 CLIPTextEncode 节点 ID: {node_id}")
                break

    # 修改提示词内容
    if prompt_node_id:
        if "inputs" not in workflow[prompt_node_id]: workflow[prompt_node_id]["inputs"] = {}
        class_type = workflow[prompt_node_id].get("class_type")
        if class_type == "WeiLinComfyUIPromptToLoras":
            workflow[prompt_node_id]["inputs"]["positive"] = positive
            workflow[prompt_node_id]["inputs"]["negative"] = negative or ""
        elif class_type == "CLIPTextEncode":
            workflow[prompt_node_id]["inputs"]["text"] = positive
        else:
            workflow[prompt_node_id]["inputs"]["text"] = positive
    else:
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncodeFlux":
                if "inputs" not in workflow[node_id]: workflow[node_id]["inputs"] = {}
                if "clip_l" in workflow[node_id]["inputs"]: workflow[node_id]["inputs"]["clip_l"] = positive
                if "t5xxl" in workflow[node_id]["inputs"]: workflow[node_id]["inputs"]["t5xxl"] = positive
                break

    # ==========================================
    # 2. 修改种子 (Seed)
    # ==========================================
    if seed is None:
        seed = random.randint(1, 999999999999999)
    
    # 适配策略: RandomNoise (针对本次工作流) > KSampler
    seed_set = False
    
    # 优先查找 RandomNoise
    for node_id, node in workflow.items():
        if node.get("class_type") == "RandomNoise":
            if "inputs" not in workflow[node_id]: workflow[node_id]["inputs"] = {}
            workflow[node_id]["inputs"]["noise_seed"] = seed
            logger.info(f"已修改 RandomNoise 节点 ID: {node_id} (Seed: {seed})")
            seed_set = True
            break
            
    if not seed_set:
        # 查找 KSampler
        for node_id, node in workflow.items():
            if node.get("class_type") == "KSampler":
                if "inputs" not in workflow[node_id]: workflow[node_id]["inputs"] = {}
                workflow[node_id]["inputs"]["seed"] = seed
                logger.info(f"已修改 KSampler 节点 ID: {node_id} (Seed: {seed})")
                break

    # ==========================================
    # 3. 确保有图像保存节点 (SaveImage)
    # ==========================================
    has_save_image = False
    for node_id, node in workflow.items():
        if node.get("class_type") == "SaveImage":
            has_save_image = True
            break
    
    if not has_save_image:
        logger.info("未检测到 SaveImage 节点，正在动态注入...")
        # 寻找图像源：PreviewImage 的输入，或 VAE Decode 的输出
        source_node_id = None
        source_output_index = 0
        
        # 策略: 找 PreviewImage 的输入
        for node_id, node in workflow.items():
            if node.get("class_type") == "PreviewImage":
                images_input = node.get("inputs", {}).get("images")
                if isinstance(images_input, list) and len(images_input) == 2:
                    source_node_id = images_input[0]
                    source_output_index = images_input[1]
                    logger.info(f"从 PreviewImage (ID: {node_id}) 追踪到图像源: {source_node_id}")
                    break
        
        if source_node_id:
            # 生成新 ID
            new_id = str(max([int(k) for k in workflow.keys() if k.isdigit()] + [0]) + 1)
            workflow[new_id] = {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "MCP_Batik",
                    "images": [source_node_id, source_output_index]
                },
                "_meta": {
                    "title": "MCP Auto SaveImage"
                }
            }
            logger.info(f"已注入 SaveImage 节点 ID: {new_id}")

    # ==========================================
    # 4. 发送请求
    # ==========================================
    comfyui_host = get_host("COMFYUI_HOST", "127.0.0.1")
    comfyui_port = get_port("comfyui_port", 8188)
    comfyui_url = build_local_url("comfyui_port", comfyui_port, "/prompt", host_env="COMFYUI_HOST", default_host=comfyui_host, url_env="COMFYUI_PROMPT_URL")
    client_id = str(uuid.uuid4())
    body = {
        "client_id": client_id,
        "prompt": workflow
    }

    try:
        # trust_env=False 防止 httpx 读取系统代理设置
        async with httpx.AsyncClient(trust_env=False) as client:
            logger.info(f"正在发送请求到 {comfyui_url}...")
            infer_start_time = iso_utc_ms_now()  # performance experiment logging
            resp = await client.post(comfyui_url, json=body, timeout=30.0)
            resp.raise_for_status()
            resp_data = resp.json()
            prompt_id = resp_data.get("prompt_id")
            logger.info(f"生成任务已提交，prompt_id: {prompt_id}，开始轮询结果...")
            
            # 轮询等待生成完成 (设置 TIMEOUT_SECONDS 秒超时)
            for _ in range(TIMEOUT_SECONDS):
                await asyncio.sleep(1)
                try:
                    history_url = build_local_url("comfyui_port", comfyui_port, f"/history/{prompt_id}", host_env="COMFYUI_HOST", default_host=comfyui_host, url_env=None)
                    history_resp = await client.get(history_url)
                    if history_resp.status_code == 200:
                        history_data = history_resp.json()
                        if prompt_id in history_data:
                            # 任务完成，提取文件名
                            outputs = history_data[prompt_id].get("outputs", {})
                            
                            # 收集所有生成的图片信息
                            generated_images = []
                            
                            for node_id, node_output in outputs.items():
                                if "images" in node_output:
                                    for image in node_output["images"]:
                                        filename = image.get("filename")
                                        subfolder = image.get("subfolder", "")
                                        img_type = image.get("type", "output")
                                        
                                        # 确定基础目录
                                        if img_type == "temp":
                                            # 如果是临时图片，尝试定位到 ComfyUI/temp 目录
                                            # 假设 COMFYUI_OUTPUT_DIR 是 .../ComfyUI/output
                                            base_dir = os.path.abspath(os.path.join(COMFYUI_OUTPUT_DIR, "../temp"))
                                        else:
                                            base_dir = COMFYUI_OUTPUT_DIR
                                            
                                        # 构建完整路径
                                        if subfolder:
                                            full_path = os.path.join(base_dir, subfolder, filename)
                                        else:
                                            full_path = os.path.join(base_dir, filename)
                                            
                                        generated_images.append({
                                            "path": full_path,
                                            "type": img_type
                                        })
                                        logger.info(f"追踪到图片: {filename} (Type: {img_type}) -> {full_path}")
                            
                            # 策略：优先返回 type='output' 的图片 (SaveImage 节点)
                            # 如果没有，再返回 type='temp' 的图片 (PreviewImage 节点)
                            final_image_path = None
                            
                            # 1. 找 Output
                            for img in generated_images:
                                if img["type"] == "output" and os.path.exists(img["path"]):
                                    final_image_path = img["path"]
                                    logger.info(f"选中 Output 图片: {final_image_path}")
                                    break
                            
                            # 2. 没找到 Output，找 Temp
                            if not final_image_path:
                                for img in generated_images:
                                    if img["type"] == "temp":
                                        if os.path.exists(img["path"]):
                                            final_image_path = img["path"]
                                            logger.info(f"选中 Temp 图片: {final_image_path}")
                                            break
                                        else:
                                            logger.warning(f"Temp 图片路径不存在: {img['path']}")
                                        
                            if final_image_path:
                                try:
                                    accessible = os.path.isfile(final_image_path) and os.path.getsize(final_image_path) > 0
                                    if accessible:
                                        with open(final_image_path, 'rb'):
                                            pass
                                except Exception:
                                    accessible = False
                                if accessible:
                                    infer_end_time = iso_utc_ms_now()  # performance experiment logging
                                    append_jsonl(SSE_LOG_PATH, {
                                        "module": "sdxl_sse",
                                        "run_id": run_id,
                                        "prompt_id": prompt_id,
                                        "mcp_receive_time": mcp_receive_time,
                                        "infer_start_time": infer_start_time,
                                        "infer_end_time": infer_end_time,
                                        "final_image_path": final_image_path,
                                        "success": True,
                                        "error_type": None
                                    })
                                    return final_image_path
                                else:
                                    logger.info("生成文件尚不可访问，继续轮询...")  # performance experiment logging
                            else:
                                # 只有路径但文件不存在的情况
                                if generated_images:
                                    logger.warning(f"文件可能未写入磁盘，尝试返回第一个路径: {generated_images[0]['path']}")
                                    append_jsonl(SSE_LOG_PATH, {
                                        "module": "sdxl_sse",
                                        "run_id": run_id,
                                        "prompt_id": prompt_id,
                                        "mcp_receive_time": mcp_receive_time,
                                        "infer_start_time": infer_start_time,
                                        "success": False,
                                        "error_type": "E1",
                                        "error_message": "Only fallback path available; file not verified"
                                    })
                                    return generated_images[0]['path']
                            
                            # 如果有历史记录但没找到图片
                            return f"任务完成但未找到输出图片 (Prompt ID: {prompt_id})"
                            
                except Exception as poll_err:
                    pass
            
            append_jsonl(SSE_LOG_PATH, {
                "module": "sdxl_sse",
                "run_id": run_id,
                "prompt_id": prompt_id,
                "mcp_receive_time": mcp_receive_time,
                "infer_start_time": infer_start_time,
                "success": False,
                "error_type": "E4",
                "error_message": "timeout"
            })  # performance experiment logging
            return f"超时: {TIMEOUT_SECONDS}秒内未获取到生成结果 (Prompt ID: {prompt_id})"

    except Exception as e:
        logger.error(f"发送 ComfyUI 请求失败: {str(e)}")
        append_jsonl(SSE_LOG_PATH, {
            "module": "sdxl_sse",
            "run_id": run_id,
            "prompt_id": prompt_id,
            "mcp_receive_time": mcp_receive_time if 'mcp_receive_time' in locals() else None,
            "infer_start_time": infer_start_time if 'infer_start_time' in locals() else None,
            "success": False,
            "error_type": "E1",
            "error_message": str(e)
        })  # performance experiment logging
        return f"发送 ComfyUI 请求失败: {str(e)}"

if __name__ == "__main__":
    # 启动 SSE 服务
    print("启动 MCP SSE Server @ 0.0.0.0:8000 ...")
    try:
        mcp.run(transport="sse")
    except Exception as e:
        print(f"Server failed to start: {e}")
