import os
import json
import time
from datetime import datetime, timezone
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Day 13 AI Observability Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom styles for HSL tailored colors and sleek dark mode design
st.markdown("""
<style>
    .reportview-container {
        background: #0f1115;
    }
    .metric-card {
        background-color: #1a1d24;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-title {
        color: #8a929e;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 5px 0;
    }
    .metric-status {
        font-size: 0.85rem;
        font-weight: 600;
    }
    .status-pass {
        color: #00e676;
    }
    .status-fail {
        color: #ff1744;
    }
</style>
""", unsafe_allowed_html=True)

st.title("📊 Day 13 AI Observability Dashboard")
st.caption("Nguồn dữ liệu từ data/logs.jsonl | Tự động làm mới sau mỗi 5s")

LOG_PATH = "data/logs.jsonl"

def load_logs():
    if not os.path.exists(LOG_PATH):
        return []
    records = []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records

records = load_logs()

if not records:
    st.warning("Chưa tìm thấy bản ghi log nào. Vui lòng chạy load test để sinh log.")
else:
    df = pd.DataFrame(records)
    # Parse timestamps
    df["dt"] = pd.to_datetime(df["ts"])
    df["minute"] = df["dt"].dt.floor("Min")
    
    # Filter last 60 minutes
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - pd.Timedelta(minutes=60)
    df_60 = df[df["dt"] >= cutoff].copy()
    
    if df_60.empty:
        df_60 = df.copy()  # Fallback to all data if none in last 60m

    # 1. LATENCY PERCENTILES
    df_resp = df_60[df_60["event"] == "response_sent"].copy()
    if not df_resp.empty:
        p50 = float(df_resp["latency_ms"].quantile(0.5))
        p95 = float(df_resp["latency_ms"].quantile(0.95))
        p99 = float(df_resp["latency_ms"].quantile(0.99))
    else:
        p50 = p95 = p99 = 0.0

    latency_ok = p95 <= 3000

    # 2. TRAFFIC (requests per minute)
    df_req = df_60[df_60["event"] == "request_received"].copy()
    if not df_req.empty:
        traffic_by_min = df_req.groupby("minute").size()
        avg_traffic = float(traffic_by_min.mean())
    else:
        traffic_by_min = pd.Series(dtype=int)
        avg_traffic = 0.0
    
    traffic_ok = avg_traffic >= 1.0

    # 3. ERRORS (error rate and breakdown)
    df_fail = df_60[df_60["event"] == "request_failed"].copy()
    req_count = len(df_req)
    fail_count = len(df_fail)
    error_rate = (fail_count / req_count * 100) if req_count > 0 else 0.0
    error_ok = error_rate <= 2.0

    # 4. COST OVER TIME
    if not df_resp.empty:
        total_cost = float(df_resp["cost_usd"].sum())
        cost_by_min = df_resp.groupby("minute")["cost_usd"].sum()
    else:
        total_cost = 0.0
        cost_by_min = pd.Series(dtype=float)
    
    cost_ok = total_cost <= 2.5

    # 5. INPUT/OUTPUT TOKENS
    if not df_resp.empty:
        total_tokens_in = int(df_resp["tokens_in"].sum())
        total_tokens_out = int(df_resp["tokens_out"].sum())
        total_tokens = total_tokens_in + total_tokens_out
        tokens_by_min = df_resp.groupby("minute")[["tokens_in", "tokens_out"]].sum()
    else:
        total_tokens_in = total_tokens_out = total_tokens = 0
        tokens_by_min = pd.DataFrame(columns=["tokens_in", "tokens_out"])
    
    tokens_ok = total_tokens <= 50000

    # 6. QUALITY PROXY (mean quality score)
    if not df_resp.empty:
        mean_quality = float(df_resp["quality_score"].mean())
    else:
        mean_quality = 0.0
    
    quality_ok = mean_quality >= 0.75

    # Layout for 6 panels
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    # Helper function to render cards
    def render_metric_card(col, title, value_str, status_str, is_ok):
        status_class = "status-pass" if is_ok else "status-fail"
        status_text = "🟢 ĐẠT" if is_ok else "🔴 VƯỢT NGƯỠNG"
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value_str}</div>
            <div class="metric-status">{status_str} | <span class="{status_class}">{status_text}</span></div>
        </div>
        """, unsafe_allowed_html=True)

    render_metric_card(col1, "1. Latency Percentiles (P50 / P95 / P99)", f"{p50:.1f} / {p95:.1f} / {p99:.1f} ms", f"Ngưỡng P95: ≤ 3000 ms", latency_ok)
    render_metric_card(col2, "2. Request Traffic (Avg/min)", f"{avg_traffic:.2f} req/m", "Ngưỡng traffic: ≥ 1 req/m", traffic_ok)
    render_metric_card(col3, "3. Error Rate & Breakdown", f"{error_rate:.2f}%", f"Thất bại: {fail_count}/{req_count} req | Ngưỡng: ≤ 2%", error_ok)
    render_metric_card(col4, "4. Cost Over Time (Total)", f"${total_cost:.6f}", "Ngưỡng tổng cost: ≤ $2.50", cost_ok)
    render_metric_card(col5, "5. Total Tokens (In / Out)", f"{total_tokens} ({total_tokens_in} / {total_tokens_out})", "Ngưỡng: ≤ 50,000 tokens", tokens_ok)
    render_metric_card(col6, "6. Quality Proxy (Mean)", f"{mean_quality:.2f}", "Ngưỡng chất lượng: ≥ 0.75", quality_ok)

    st.write("---")

    # Detailed Charts
    char_col1, char_col2 = st.columns(2)

    with char_col1:
        st.subheader("Trực quan hóa Latency qua từng phút (ms)")
        if not df_resp.empty:
            latency_chart = df_resp.groupby("minute")["latency_ms"].agg(["mean", "max"]).rename(columns={"mean": "Avg Latency", "max": "Max Latency"})
            st.line_chart(latency_chart)
        else:
            st.info("Chưa có dữ liệu vẽ biểu đồ latency.")

    with char_col2:
        st.subheader("Traffic & Lỗi theo phút")
        if not df_60.empty:
            traffic_chart = pd.DataFrame({
                "Received": df_60[df_60["event"] == "request_received"].groupby("minute").size(),
                "Failed": df_fail.groupby("minute").size()
            }).fillna(0)
            st.bar_chart(traffic_chart)
        else:
            st.info("Chưa có dữ liệu vẽ biểu đồ traffic.")

    # Show error types breakdown if any errors
    if not df_fail.empty:
        st.subheader("Chi tiết lỗi phát sinh")
        err_breakdown = df_fail["error_type"].value_counts().rename_axis("Mã lỗi").reset_index(name="Số lượng")
        st.dataframe(err_breakdown, use_container_width=True)

# Auto refresh script
time.sleep(5)
st.rerun()
