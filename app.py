%%writefile app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import websocket
import json
import threading
import time
from datetime import datetime

# Cấu hình trang Streamlit
st.set_page_config(
    page_title="Kraken Live Monitor",
    page_icon="⚡",
    layout="wide"
)

# Khởi tạo dữ liệu ban đầu
if "live_prices" not in st.session_state:
    st.session_state["live_prices"] = {
        "BTC/USD": 60000.0,
        "ETH/USD": 3000.0,
        "SOL/USD": 140.0,
        "ADA/USD": 0.40,
    }

# Kết nối Websocket Kraken ngầm
def on_message(ws, message):
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            pair = data[-1]
            price_info = data[1]
            if "c" in price_info:
                last_price = float(price_info["c"][0])
                if "XBT" in pair or "BTC" in pair:
                    st.session_state["live_prices"]["BTC/USD"] = last_price
                elif "ETH" in pair:
                    st.session_state["live_prices"]["ETH/USD"] = last_price
                elif "SOL" in pair:
                    st.session_state["live_prices"]["SOL/USD"] = last_price
                elif "ADA" in pair:
                    st.session_state["live_prices"]["ADA/USD"] = last_price
    except Exception:
        pass

def start_ws():
    ws_url = "wss://ws.kraken.com"
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_open=lambda ws: ws.send(json.dumps({
            "event": "subscribe",
            "pair": ["XBT/USD", "ETH/USD", "SOL/USD", "XRP/USD"],
            "subscription": {"name": "ticker"}
        }))
    )
    ws.run_forever()

if "ws_thread" not in st.session_state:
    t = threading.Thread(target=start_ws, daemon=True)
    t.start()
    st.session_state["ws_thread"] = True

# Giao diện Web
st.title("⚡ KRAKEN WEBSOCKET LIVE MONITOR")
st.caption("Dữ liệu trực tiếp (Real-Time) từ sàn Kraken qua kết nối WebSocket")

now_str = datetime.now().strftime("%H:%M:%S")
st.warning(f"🔴 WebSocket LIVE — Thời gian cập nhật: {now_str}")

# Biểu đồ Plotly
df = pd.DataFrame(list(st.session_state["live_prices"].items()), columns=["Coin", "Price_USD"])
fig = px.bar(
    df, x="Coin", y="Price_USD", color="Coin",
    text=df["Price_USD"].apply(lambda x: f"${x:,.2f}"),
    title="Giá Real-Time Từng Giây (Thang đo Log Scale)",
    template="plotly_dark"
)
fig.update_layout(yaxis=dict(type="log"))
st.plotly_chart(fig, use_container_width=True)

# Tự động làm mới trang mỗi 2 giây
time.sleep(2)
st.rerun()
