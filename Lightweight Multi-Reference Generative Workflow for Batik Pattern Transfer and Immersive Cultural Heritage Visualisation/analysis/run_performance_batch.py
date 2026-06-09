# 批量触发 4.4 系统性能实验（仅触发，不改业务逻辑）
# 作用：连续调用配置后的 orchestrator `/generate_then_update` 共 30 次，每次间隔 2 秒
# 成功判定：HTTP 200 且响应正文不包含失败关键词（fail/error/timeout/超时/失败）
# 输出：终端打印每轮开始/结束时间、状态与响应前缀；最后打印成功/失败次数
#
# 运行示例（Windows）：
#   python analysis/run_performance_batch.py

import time
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import build_local_url

URL = build_local_url("orchestrator_trigger_port", 3002, "/generate_then_update", url_env="MCP_ORCHESTRATOR_TRIGGER_URL")
TOTAL = 30
SLEEP_INTERVAL = 2.0
TIMEOUT = 10.0

FAIL_KEYWORDS = ["fail", "error", "timeout", "超时", "失败"]

def iso_utc_ms_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def post_json(url, body_obj, timeout=10.0):
    data = json.dumps(body_obj).encode("utf-8")
    req = Request(url=url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        content_bytes = resp.read()
        # 兼容文本返回，截取前缀用于打印
        try:
            content_text = content_bytes.decode("utf-8", errors="ignore")
        except Exception:
            content_text = ""
        return status, content_text

def main():
    success = 0
    fail = 0
    print(f"开始批量触发：共 {TOTAL} 次，目标 {URL}")

    for i in range(1, TOTAL + 1):
        start_ts = iso_utc_ms_now()
        status = None
        text = ""
        ok = False
        err_msg = ""

        try:
            status, text = post_json(URL, {}, timeout=TIMEOUT)
            # 成功判定：HTTP 200 且无失败关键词
            text_lower = (text or "").lower()
            matched_fail = any(k in text_lower for k in FAIL_KEYWORDS)
            ok = (status == 200) and (not matched_fail)
            if not ok and matched_fail:
                err_msg = "keyword-match-fail"
        except HTTPError as e:
            status = e.code
            err_msg = f"HTTPError {e.code}"
        except URLError as e:
            err_msg = f"URLError {e.reason}"
        except Exception as e:
            err_msg = f"Exception {e}"

        end_ts = iso_utc_ms_now()
        prefix = (text[:80] if isinstance(text, str) else str(text)[:80]).replace("\n", " ")
        if ok:
            success += 1
            print(f"Run {i}/{TOTAL} start={start_ts} end={end_ts} OK {status} resp='{prefix}'")
        else:
            fail += 1
            print(f"Run {i}/{TOTAL} start={start_ts} end={end_ts} FAIL status={status} reason={err_msg} resp='{prefix}'")

        time.sleep(SLEEP_INTERVAL)

    print(f"完成：Success={success} Fail={fail}")

if __name__ == "__main__":
    main()
