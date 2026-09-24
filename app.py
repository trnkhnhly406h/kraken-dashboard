%%writefile app.py
from datetime import datetime
import json
import threading
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import websocket

# ==========================================
# 1. CẤU HÌNH TRANG WEB STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Crypto Quant & Risk Analytics Terminal",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS cho giao diện hầm hố chuẩn Terminal tài chính
st.markdown(
    """
    <style>
    .stApp { background-color: #0E1117; }
    .metric-card {
        background-color: #1E222D;
        border: 1px solid #2A2E39;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. KHỞI TẠO STATE & WEBSOCKET KRAKEN
# ==========================================
MAX_DATA_POINTS = 100

if "price_data" not in st.session_state:
    st.session_state.price_data = []

if "selected_pair" not in st.session_state:
    st.session_state.selected_pair = "XBT/USD"


def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            price_info = data[1]
            if "c" in price_info:
                last_price = float(price_info["c"][0])
                timestamp = pd.Timestamp.now().strftime("%H:%M:%S")

                st.session_state.price_data.append(
                    {"Time": timestamp, "Price": last_price}
                )

                if len(st.session_state.price_data) > MAX_DATA_POINTS:
                    st.session_state.price_data.pop(0)
    except Exception:
        pass


def start_websocket():
    ws_url = "wss://ws.kraken.com"
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_open=lambda ws: ws.send(
            json.dumps(
                {
                    "event": "subscribe",
                    "pair": ["XBT/USD"],
                    "subscription": {"name": "ticker"},
                }
            )
        ),
    )
    ws.run_forever()


@st.cache_resource
def init_ws():
    t = threading.Thread(target=start_websocket, daemon=True)
    t.start()
    return t


init_ws()


# ==========================================
# 3. THUẬT TOÁN ĐỊNH LƯỢNG (QUANTITATIVE ENGINE)
# ==========================================
def calculate_metrics(df, window=10):
    if len(df) < 2:
        return df

    # 1. Simple Moving Average (SMA) & Standard Deviation
    df["SMA"] = df["Price"].rolling(window=window, min_periods=1).mean()
    df["STD"] = df["Price"].rolling(window=window, min_periods=1).std().fillna(0)

    # 2. Bollinger Bands (2*STD)
    df["Upper_Band"] = df["SMA"] + (df["STD"] * 2)
    df["Lower_Band"] = df["SMA"] - (df["STD"] * 2)

    # 3. Volatility (%)
    df["Volatility"] = (df["STD"] / df["SMA"]) * 100

    # 4. Relative Strength Index (RSI - 14 periods)
    delta = df["Price"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))

    return df


# ==========================================
# 4. THANH SIDEBAR TƯƠNG TÁC (CONTROL PANEL)
# ==========================================
with st.sidebar:
    st.title("⚙️ Cấu Hình Hệ Thống")
    st.divider()

    st.subheader("1. Tham Số Định Lượng")
    sma_window = st.slider(
        "Chu kỳ SMA / Bollinger", min_value=5, max_value=30, value=10
    )
    volatility_alert_threshold = st.number_input(
        "Ngưỡng Cảnh Báo Volatility (%)", value=0.05, step=0.01
    )

    st.divider()
    st.subheader("2. Thông Tin Luồng Dữ Liệu")
    st.success("🟢 WebSocket Status: CONNECTED")
    st.info("Nguồn dữ liệu: Kraken Exchange API (`wss://ws.kraken.com`)")
    st.caption("Cặp giao dịch: BTC/USD (Bitcoin)")

# ==========================================
# 5. GIAO DIỆN DASHBOARD CHÍNH
# ==========================================
st.title("📊 Real-Time Financial Quant & Risk Analytics Terminal")
st.markdown(
    "Hệ thống theo dõi & phân tích chỉ số định lượng thời gian thực sử dụng WebSocket, Bollinger Bands & RSI."
)
st.divider()

metric_placeholder = st.empty()
chart_placeholder = st.empty()
data_table_placeholder = st.empty()

# Vòng lặp Real-Time Updates
while True:
    data_list = list(st.session_state.price_data)

    if len(data_list) > 0:
        df = pd.DataFrame(data_list)
        df = calculate_metrics(df, window=sma_window)

        curr_price = df["Price"].iloc[-1]
        prev_price = df["Price"].iloc[-2] if len(df) > 1 else curr_price
        price_delta = curr_price - prev_price

        curr_sma = df["SMA"].iloc[-1]
        curr_volatility = df["Volatility"].iloc[-1]
        curr_rsi = df["RSI"].iloc[-1] if "RSI" in df.columns else 50.0

        # A. KHU VỰC THẺ CHỈ SỐ KPI (METRICS CARDS)
        with metric_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            col1.metric(
                "Giá BTC/USD Real-Time",
                f"${curr_price:,.2f}",
                f"{price_delta:+,.2f} USD",
            )
            col2.metric(
                "Đường SMA (" + str(sma_window) + " kỳ)", f"${curr_sma:,.2f}"
            )
            col3.metric(
                "Volatility (Độ biến động)", f"{curr_volatility:.4f}%"
            )
            col4.metric(
                "Chỉ số RSI (14)",
                f"{curr_rsi:.1f}",
                delta="Quá Mua (>70)"
                if curr_rsi > 70
                else ("Quá Bán (<30)" if curr_rsi < 30 else "Trung tính"),
                delta_color="inverse" if curr_rsi > 70 else "normal",
            )

            # Cảnh báo rủi ro biến động mạnh
            if curr_volatility > volatility_alert_threshold:
                st.warning(
                    f"⚠️ **CẢNH BÁO RỦI RO:** Độ biến động thị trường ({curr_volatility:.4f}%) vượt ngưỡng an toàn ({volatility_alert_threshold}%)!"
                )

        # B. KHU VỰC BIỂU ĐỒ NÂNG CẠO (MULTI-SUBPLOT CHART)
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Biểu Đồ Giá Real-Time & Dải Bollinger Bands",
                "Chỉ Số Sức Mạnh Tương Quan (RSI)",
            ),
            row_heights=[0.7, 0.3],
        )

        # Subplot 1: Upper / Lower Band (Bóng mờ)
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Upper_Band"],
                name="Upper Band",
                line=dict(color="rgba(255, 215, 0, 0.4)", dash="dash"),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Lower_Band"],
                name="Lower Band",
                line=dict(color="rgba(255, 215, 0, 0.4)", dash="dash"),
                fill="tonexty",
                fillcolor="rgba(255, 215, 0, 0.05)",
            ),
            row=1,
            col=1,
        )

        # Subplot 1: Price & SMA
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["Price"],
                name="Giá Live",
                line=dict(color="#00E676", width=2.5),
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["SMA"],
                name=f"SMA ({sma_window})",
                line=dict(color="#FF5252", width=1.5),
            ),
            row=1,
            col=1,
        )

        # Subplot 2: RSI Chart
        fig.add_trace(
            go.Scatter(
                x=df["Time"],
                y=df["RSI"],
                name="RSI (14)",
                line=dict(color="#29B6F6", width=2),
            ),
            row=2,
            col=1,
        )
        fig.add_hline(
            y=70,
            line_dash="dot",
            line_color="red",
            annotation_text="Quá mua (70)",
            row=2,
            col=1,
        )
        fig.add_hline(
            y=30,
            line_dash="dot",
            line_color="green",
            annotation_text="Quá bán (30)",
            row=2,
            col=1,
        )

        fig.update_layout(
            template="plotly_dark",
            height=600,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified",
            showlegend=True,
        )
        fig.update_yaxes(title_text="Giá USD ($)", row=1, col=1)
        fig.update_yaxes(title_text="Chỉ số RSI", range=[0, 100], row=2, col=1)

        with chart_placeholder.container():
            st.plotly_chart(fig, use_container_width=True)

        # C. BẢNG CHI TIẾT DỮ LIỆU STREAMING
        with data_table_placeholder.container():
            with st.expander("📋 Xem chi tiết dữ liệu 10 mẫu gần nhất (Streaming Table)"):
                st.dataframe(
                    df[["Time", "Price", "SMA", "Upper_Band", "Lower_Band", "Volatility", "RSI"]]
                    .tail(10)
                    .sort_index(ascending=False),
                    use_container_width=True,
                )

    time.sleep(1)
