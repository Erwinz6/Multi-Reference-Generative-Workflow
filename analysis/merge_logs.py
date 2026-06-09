# performance experiment logging - merge only
# Merges four JSONL logs by run_id into a single CSV for downstream analysis.
# Inputs (default):
#   <repo>/logs/orchestrator_log.jsonl
#   <repo>/logs/sdxl_sse_log.jsonl
#   <repo>/logs/bridge_log.jsonl
#   <repo>/logs/ue_listener_log.jsonl
# Output:
#   <repo>/analysis/merged_runs.csv
#
# Run (Windows):
#   python analysis/merge_logs.py
#
# Notes:
# - Uses run_id as the primary key.
# - Keeps last record if duplicates appear within the same module.
# - Marks status: complete (orchestrator + sse + ue present) or partial.
# - bridge is merged for diagnostics only, not used for status.
# - Adds duplicate_flag (any module duplicated) and time_anomaly mark.
# - Adds merge_note to capture missing/duplicate notes like: missing_sse;duplicate_in_ue
# - Adds complete_for_main_stats = 1 when (orchestrator+sse+ue) are all present.

import os
import json
import csv
import sys
from pathlib import Path
from datetime import datetime

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from common.repo_config import get_log_dir

# Default paths
ROOT = str(REPO_ROOT)
LOG_DIR = str(get_log_dir())
OUT_DIR = os.path.join(ROOT, "analysis")
OUT_CSV = os.path.join(OUT_DIR, "merged_runs.csv")

ORC_PATH = os.path.join(LOG_DIR, "orchestrator_log.jsonl")
SSE_PATH = os.path.join(LOG_DIR, "sdxl_sse_log.jsonl")
BRI_PATH = os.path.join(LOG_DIR, "bridge_log.jsonl")
UE_PATH  = os.path.join(LOG_DIR, "ue_listener_log.jsonl")

# Columns to emit (meta first)
COLUMNS = [
    "run_id", "status", "complete_for_main_stats", "duplicate_flag", "time_anomaly", "merge_note",
    # orchestrator
    "o_prompt_id", "o_trigger_time", "o_request_sent_time", "o_success", "o_error_type", "o_ue_feedback_text",
    # sse
    "sse_prompt_id", "sse_mcp_receive_time", "sse_infer_start_time", "sse_infer_end_time",
    "sse_final_image_path", "sse_success", "sse_error_type", "sse_error_message",
    # ue
    "ue_prompt_id", "ue_recv_time", "ue_update_done_time", "ue_success",
    "ue_image_path", "ue_material_name", "ue_error_type", "ue_error_message",
    # bridge (diagnostics)
    "bridge_prompt_id", "bridge_dispatch_time", "bridge_return_time", "bridge_success",
    "bridge_image_path", "bridge_ue_response_text", "bridge_error_type", "bridge_error_message",
]

def read_jsonl(path):
    items = []
    if not os.path.isfile(path):
        return items
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                items.append(obj)
            except Exception:
                continue
    return items

def iso_to_dt(s):
    if not s or not isinstance(s, str):
        return None
    try:
        # Accept ISO with 'Z' or timezone offset
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None

def collect_by_run(items, module_name, duplicates_counter):
    """
    Keep only the last entry per run_id for a given module.
    Returns:
      per_run: dict run_id -> last record
      dup_ids: set of run_ids that appeared more than once
    Also updates duplicates_counter[module_name] = len(dup_ids).
    """
    per_run = {}
    seen_counts = {}
    for obj in items:
        rid = obj.get("run_id")
        if not rid:
            continue
        if rid in per_run:
            seen_counts[rid] = seen_counts.get(rid, 1) + 1
        per_run[rid] = obj
    dup_ids = {rid for rid, c in seen_counts.items() if c >= 2}
    duplicates_counter[module_name] = len(dup_ids)
    return per_run, dup_ids

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    duplicates_counter = {"orchestrator":0, "sse":0, "bridge":0, "ue":0}

    orc_items = read_jsonl(ORC_PATH)
    sse_items = read_jsonl(SSE_PATH)
    bri_items = read_jsonl(BRI_PATH)
    ue_items  = read_jsonl(UE_PATH)

    orc_by, orc_dups = collect_by_run(orc_items, "orchestrator", duplicates_counter)
    sse_by, sse_dups = collect_by_run(sse_items, "sse", duplicates_counter)
    bri_by, bri_dups = collect_by_run(bri_items, "bridge", duplicates_counter)
    ue_by,  ue_dups  = collect_by_run(ue_items,  "ue", duplicates_counter)

    all_run_ids = set().union(orc_by.keys(), sse_by.keys(), bri_by.keys(), ue_by.keys())

    rows = []
    missing_counts = {"orchestrator":0, "sse":0, "bridge":0, "ue":0}
    duplicate_flag_total = 0
    complete_count = 0

    for rid in sorted(all_run_ids):
        o = orc_by.get(rid)
        s = sse_by.get(rid)
        b = bri_by.get(rid)
        u = ue_by.get(rid)

        note_parts = []
        if o is None: 
            missing_counts["orchestrator"] += 1
            note_parts.append("missing_orchestrator")
        if s is None: 
            missing_counts["sse"] += 1
            note_parts.append("missing_sse")
        if u is None: 
            missing_counts["ue"] += 1
            note_parts.append("missing_ue")
        if b is None: 
            missing_counts["bridge"] += 1
            note_parts.append("missing_bridge")

        # duplicate flag via dup sets
        dup_sources = []
        if rid in orc_dups: dup_sources.append("orchestrator")
        if rid in sse_dups: dup_sources.append("sse")
        if rid in bri_dups: dup_sources.append("bridge")
        if rid in ue_dups:  dup_sources.append("ue")
        dup_flag = 1 if dup_sources else 0
        if dup_flag:
            duplicate_flag_total += 1
            note_parts.extend([f"duplicate_in_{m}" for m in dup_sources])

        status = "complete" if (o and s and u) else "partial"
        complete_for_main_stats = 1 if status == "complete" else 0

        # time anomaly checks (best effort)
        def T(a, b):  # returns 1 if b < a
            da, db = iso_to_dt(a), iso_to_dt(b)
            return 1 if (da and db and db < da) else 0

        time_anomaly = 0
        # T1
        if o:
            time_anomaly |= T(o.get("trigger_time"), o.get("request_sent_time"))
        # T2, T3
        if s:
            time_anomaly |= T(s.get("mcp_receive_time"), s.get("infer_start_time"))
            time_anomaly |= T(s.get("infer_start_time"), s.get("infer_end_time"))
        # T4
        if s and u:
            time_anomaly |= T(s.get("infer_end_time"), u.get("recv_time"))
        # T5 (mandatory check, previously missing)
        if u:
            time_anomaly |= T(u.get("recv_time"), u.get("update_done_time"))
        # T_total
        if u and o:
            time_anomaly |= T(o.get("trigger_time"), u.get("update_done_time"))

        rows.append({
            # meta
            "run_id": rid,
            "status": status,
            "complete_for_main_stats": complete_for_main_stats,
            "duplicate_flag": dup_flag,
            "time_anomaly": time_anomaly,
            "merge_note": ";".join(note_parts) if note_parts else "",
            # orchestrator
            "o_prompt_id": (o or {}).get("prompt_id"),
            "o_trigger_time": (o or {}).get("trigger_time"),
            "o_request_sent_time": (o or {}).get("request_sent_time"),
            "o_success": (o or {}).get("success"),
            "o_error_type": (o or {}).get("error_type"),
            "o_ue_feedback_text": (o or {}).get("ue_feedback_text"),
            # sse
            "sse_prompt_id": (s or {}).get("prompt_id"),
            "sse_mcp_receive_time": (s or {}).get("mcp_receive_time"),
            "sse_infer_start_time": (s or {}).get("infer_start_time"),
            "sse_infer_end_time": (s or {}).get("infer_end_time"),
            "sse_final_image_path": (s or {}).get("final_image_path"),
            "sse_success": (s or {}).get("success"),
            "sse_error_type": (s or {}).get("error_type"),
            "sse_error_message": (s or {}).get("error_message"),
            # ue
            "ue_prompt_id": (u or {}).get("prompt_id"),
            "ue_recv_time": (u or {}).get("recv_time"),
            "ue_update_done_time": (u or {}).get("update_done_time"),
            "ue_success": (u or {}).get("success"),
            "ue_image_path": (u or {}).get("image_path"),
            "ue_material_name": (u or {}).get("material_name"),
            "ue_error_type": (u or {}).get("error_type"),
            "ue_error_message": (u or {}).get("error_message"),
            # bridge (diagnostics)
            "bridge_prompt_id": (b or {}).get("prompt_id"),
            "bridge_dispatch_time": (b or {}).get("dispatch_time"),
            "bridge_return_time": (b or {}).get("return_time"),
            "bridge_success": (b or {}).get("success"),
            "bridge_image_path": (b or {}).get("image_path"),
            "bridge_ue_response_text": (b or {}).get("ue_response_text"),
            "bridge_error_type": (b or {}).get("error_type"),
            "bridge_error_message": (b or {}).get("error_message"),
        })

        if status == "complete":
            complete_count += 1

    # Write CSV
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Print summary
    total_runs = len(rows)
    partial_count = total_runs - complete_count
    print(f"Merged runs: {total_runs}")
    print(f"complete: {complete_count}")
    print(f"partial: {partial_count}")
    print(f"duplicates (any module): {duplicate_flag_total}")
    print(f"duplicates by module: orchestrator={duplicates_counter.get('orchestrator',0)}, "
          f"sse={duplicates_counter.get('sse',0)}, bridge={duplicates_counter.get('bridge',0)}, "
          f"ue={duplicates_counter.get('ue',0)}")
    print(f"missing by module: orchestrator={missing_counts['orchestrator']}, "
          f"sse={missing_counts['sse']}, bridge={missing_counts['bridge']}, ue={missing_counts['ue']}")
    print(f"Output: {OUT_CSV}")

if __name__ == "__main__":
    main()
