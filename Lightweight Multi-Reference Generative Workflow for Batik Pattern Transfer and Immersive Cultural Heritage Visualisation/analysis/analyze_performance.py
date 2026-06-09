# 4.4.1 端到端响应时间分析（performance experiment logging）
# 输入：<repo>/analysis/merged_runs.csv
# 输出：
#   <repo>/analysis/performance_detail.csv
#   <repo>/analysis/performance_summary.csv
#
# 运行示例（Windows）：
#   python analysis/analyze_performance.py

import os
import csv
import sys
from pathlib import Path
from datetime import datetime
from statistics import mean, pstdev

CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

ROOT = str(REPO_ROOT)
IN_CSV = os.path.join(ROOT, "analysis", "merged_runs.csv")
OUT_DIR = os.path.join(ROOT, "analysis")
DETAIL_CSV = os.path.join(OUT_DIR, "performance_detail.csv")
SUMMARY_CSV = os.path.join(OUT_DIR, "performance_summary.csv")

REQUIRED_FIELDS = [
    "o_trigger_time",
    "o_request_sent_time",
    "sse_mcp_receive_time",
    "sse_infer_start_time",
    "sse_infer_end_time",
    "ue_recv_time",
    "ue_update_done_time",
]

DETAIL_COLUMNS = [
    "run_id",
    "complete_for_main_stats",
    "status",
    "duplicate_flag",
    "time_anomaly",
    "time_invalid",
    "exclusion_reason",
    "T1",
    "T2",
    "T3",
    "T4",
    "T5",
    "T_total",
    "inference_ratio",
    "non_inference_ratio",
    # 原始关键时间戳（便于排查）
    "o_trigger_time",
    "o_request_sent_time",
    "sse_mcp_receive_time",
    "sse_infer_start_time",
    "sse_infer_end_time",
    "ue_recv_time",
    "ue_update_done_time",
]

SUMMARY_COLUMNS = [
    "n_valid",
    "T1_mean", "T1_sd", "T1_min", "T1_max",
    "T2_mean", "T2_sd", "T2_min", "T2_max",
    "T3_mean", "T3_sd", "T3_min", "T3_max",
    "T4_mean", "T4_sd", "T4_min", "T4_max",
    "T5_mean", "T5_sd", "T5_min", "T5_max",
    "Ttotal_mean", "Ttotal_sd", "Ttotal_min", "Ttotal_max",
    "inference_ratio_mean",
    "non_inference_ratio_mean",
]

def iso_to_dt(s):
    if not s or not isinstance(s, str):
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None

def dt_diff_sec(a, b):
    if not a or not b:
        return None
    try:
        return (b - a).total_seconds()
    except Exception:
        return None

def safe_mean(vals):
    return mean(vals) if vals else None

def safe_pstdev(vals):
    return pstdev(vals) if len(vals) > 1 else 0.0 if len(vals) == 1 else None

def load_rows(path):
    rows = []
    if not os.path.isfile(path):
        return rows
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    merged = load_rows(IN_CSV)

    total_runs = len(merged)
    complete_flag_count = sum(1 for r in merged if str(r.get("complete_for_main_stats","0")) == "1")
    time_anomaly_count = sum(1 for r in merged if str(r.get("time_anomaly","0")) == "1")

    detail_rows = []
    valid_rows_for_summary = []
    exclusion_counts = {"incomplete_run":0, "missing_field":0, "negative_duration":0}

    for r in merged:
        rid = r.get("run_id")
        complete_for_main_stats = int(r.get("complete_for_main_stats","0"))
        status = r.get("status")
        duplicate_flag = int(r.get("duplicate_flag","0"))
        time_anomaly = int(r.get("time_anomaly","0"))

        # Parse timestamps
        o_trig = iso_to_dt(r.get("o_trigger_time"))
        o_send = iso_to_dt(r.get("o_request_sent_time"))
        s_mcp  = iso_to_dt(r.get("sse_mcp_receive_time"))
        s_st   = iso_to_dt(r.get("sse_infer_start_time"))
        s_end  = iso_to_dt(r.get("sse_infer_end_time"))
        u_recv = iso_to_dt(r.get("ue_recv_time"))
        u_done = iso_to_dt(r.get("ue_update_done_time"))

        # Compute durations (seconds)
        T1 = dt_diff_sec(o_trig, o_send)
        T2 = dt_diff_sec(s_mcp, s_st)
        T3 = dt_diff_sec(s_st, s_end)
        T4 = dt_diff_sec(s_end, u_recv)
        T5 = dt_diff_sec(u_recv, u_done)
        T_total = dt_diff_sec(o_trig, u_done)

        # Validity and exclusion_reason
        time_invalid = 0
        exclusion_reason = ""

        if complete_for_main_stats != 1:
            time_invalid = 1
            exclusion_reason = "incomplete_run"
        else:
            missing = any(r.get(f, "") == "" for f in REQUIRED_FIELDS)
            if missing or None in [T1, T2, T3, T4, T5, T_total]:
                time_invalid = 1
                exclusion_reason = "missing_field"
            else:
                durations = [T1, T2, T3, T4, T5, T_total]
                if any(d is not None and d < 0 for d in durations):
                    time_invalid = 1
                    exclusion_reason = "negative_duration"

        # Ratios（仅当 T_total 有效且 > 0）
        inference_ratio = None
        non_inference_ratio = None
        if (T_total is not None) and (T_total > 0):
            if T3 is not None:
                inference_ratio = T3 / T_total
            if all(d is not None for d in [T1, T2, T4, T5]):
                non_inference_ratio = (T1 + T2 + T4 + T5) / T_total

        detail_rows.append({
            "run_id": rid,
            "complete_for_main_stats": complete_for_main_stats,
            "status": status,
            "duplicate_flag": duplicate_flag,
            "time_anomaly": time_anomaly,
            "time_invalid": time_invalid,
            "exclusion_reason": exclusion_reason,
            "T1": T1,
            "T2": T2,
            "T3": T3,
            "T4": T4,
            "T5": T5,
            "T_total": T_total,
            "inference_ratio": inference_ratio,
            "non_inference_ratio": non_inference_ratio,
            # 原始关键时间戳（便于排查）
            "o_trigger_time": r.get("o_trigger_time"),
            "o_request_sent_time": r.get("o_request_sent_time"),
            "sse_mcp_receive_time": r.get("sse_mcp_receive_time"),
            "sse_infer_start_time": r.get("sse_infer_start_time"),
            "sse_infer_end_time": r.get("sse_infer_end_time"),
            "ue_recv_time": r.get("ue_recv_time"),
            "ue_update_done_time": r.get("ue_update_done_time"),
        })

        if complete_for_main_stats == 1 and exclusion_reason == "":
            valid_rows_for_summary.append({
                "T1": T1, "T2": T2, "T3": T3, "T4": T4, "T5": T5, "T_total": T_total,
                "inference_ratio": inference_ratio, "non_inference_ratio": non_inference_ratio
            })
        else:
            if exclusion_reason:
                exclusion_counts[exclusion_reason] = exclusion_counts.get(exclusion_reason, 0) + 1

    # Write detail CSV
    with open(DETAIL_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=DETAIL_COLUMNS)
        writer.writeheader()
        for row in detail_rows:
            writer.writerow(row)

    # Summary stats helpers
    def collect(field):
        vals = [x[field] for x in valid_rows_for_summary if x[field] is not None]
        return vals

    T1_vals = collect("T1")
    T2_vals = collect("T2")
    T3_vals = collect("T3")
    T4_vals = collect("T4")
    T5_vals = collect("T5")
    Tt_vals = collect("T_total")
    IR_vals = collect("inference_ratio")
    NR_vals = collect("non_inference_ratio")

    summary = {
        "n_valid": len(valid_rows_for_summary),
        "T1_mean": safe_mean(T1_vals), "T1_sd": safe_pstdev(T1_vals), "T1_min": min(T1_vals) if T1_vals else None, "T1_max": max(T1_vals) if T1_vals else None,
        "T2_mean": safe_mean(T2_vals), "T2_sd": safe_pstdev(T2_vals), "T2_min": min(T2_vals) if T2_vals else None, "T2_max": max(T2_vals) if T2_vals else None,
        "T3_mean": safe_mean(T3_vals), "T3_sd": safe_pstdev(T3_vals), "T3_min": min(T3_vals) if T3_vals else None, "T3_max": max(T3_vals) if T3_vals else None,
        "T4_mean": safe_mean(T4_vals), "T4_sd": safe_pstdev(T4_vals), "T4_min": min(T4_vals) if T4_vals else None, "T4_max": max(T4_vals) if T4_vals else None,
        "T5_mean": safe_mean(T5_vals), "T5_sd": safe_pstdev(T5_vals), "T5_min": min(T5_vals) if T5_vals else None, "T5_max": max(T5_vals) if T5_vals else None,
        "Ttotal_mean": safe_mean(Tt_vals), "Ttotal_sd": safe_pstdev(Tt_vals), "Ttotal_min": min(Tt_vals) if Tt_vals else None, "Ttotal_max": max(Tt_vals) if Tt_vals else None,
        "inference_ratio_mean": safe_mean(IR_vals),
        "non_inference_ratio_mean": safe_mean(NR_vals),
    }

    # Write summary CSV
    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary)

    # Terminal prints
    valid_n = summary["n_valid"]
    excluded_n = sum(1 for d in detail_rows if d.get("exclusion_reason"))
    print(f"merged_runs total: {total_runs}")
    print(f"complete_for_main_stats=1: {complete_flag_count}")
    print(f"valid for summary: {valid_n}")
    print(f"excluded: {excluded_n}")
    print(f"exclusion counts: {exclusion_counts}")
    print(f"time_anomaly count: {time_anomaly_count}")

    # Paper-friendly brief
    avg_total = summary['Ttotal_mean']
    avg_t3    = summary['T3_mean']
    avg_ir    = summary['inference_ratio_mean']
    avg_nr    = summary['non_inference_ratio_mean']
    print("Performance brief (for paper):")
    print(f"- 平均总响应时间 T_total: {avg_total:.3f}s" if avg_total is not None else "- 平均总响应时间 T_total: N/A")
    print(f"- 平均模型推理时间 T3: {avg_t3:.3f}s" if avg_t3 is not None else "- 平均模型推理时间 T3: N/A")
    print(f"- 模型推理时间占比: {avg_ir:.3f}" if avg_ir is not None else "- 模型推理时间占比: N/A")
    print(f"- 非推理附加开销占比: {avg_nr:.3f}" if avg_nr is not None else "- 非推理附加开销占比: N/A")

if __name__ == "__main__":
    main()
