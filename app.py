%%writefile app.py
from datetime import datetime
import json
import threading
import time
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import websocket

# Bộ lưu trữ dữ liệu real-time từ Kraken
live_prices = {
    "BTC/USD": 60000.0,
    "ETH/USD": 3000.0,
    "SOL/USD": 140.0,
    "ADA/USD": 0.40,
}

def on_message(ws, message):
    global live_prices
    try:
        data = json.loads(message)
        if isinstance(data, list) and len(data) > 1:
            pair = data[-1]
            price_info = data[1]

            if "c" in price_info:
                last_price = float(price_info["c"][0])

                if "XBT" in pair or "BTC" in pair:
                    live_prices["BTC/USD"] = last_price
                elif "ETH" in pair:
                    live_prices["ETH/USD"] = last_price
                elif "SOL" in pair:
                    live_prices["SOL/USD"] = last_price
                elif "ADA" in pair:
                    live_prices["ADA/USD"] = last_price
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
                    "pair": [
                        "XBT/USD",
                        "ETH/USD",
                        "SOL/USD",
                        "XRP/USD",
                    ],
                    "subscription": {"name": "ticker"},
                }
            )
        ),
    )
    ws.run_forever()

t = threading.Thread(target=start_websocket, daemon=True)
t.start()

app = dash.Dash(__name__)

app.layout = html.Div(
    style={
        "backgroundColor": "#121212",
        "color": "#ffffff",
        "padding": "30px",
        "fontFamily": "Segoe UI, Arial, sans-serif",
        "minHeight": "100vh",
    },
    children=[
        html.H2(
            "⚡ KRAKEN WEBSOCKET LIVE MONITOR",
            style={
                "textAlign": "center",
                "color": "#00E676",
                "fontWeight": "bold",
            },
        ),
        html.P(
            "Dữ liệu trực tiếp (Real-Time) từ sàn Kraken qua kết nối WebSocket",
            style={
                "textAlign": "center",
                "color": "#B0BEC5",
                "fontSize": "14px",
            },
        ),
        html.Div(
            id="status-bar",
            style={
                "textAlign": "center",
                "fontSize": "18px",
                "margin": "15px",
                "color": "#FFD54F",
            },
        ),
        dcc.Graph(id="live-bar-chart", config={"displayModeBar": False}),
        dcc.Interval(id="interval", interval=1000, n_intervals=0),
    ],
)

@app.callback(
    [Output("live-bar-chart", "figure"), Output("status-bar", "children")],
    Input("interval", "n_intervals"),
)
def update_graph(n):
    df = pd.DataFrame(
        list(live_prices.items()), columns=["Coin", "Price_USD"]
    )

    now_str = datetime.now().strftime("%H:%M:%S")

    fig = px.bar(
        df,
        x="Coin",
        y="Price_USD",
        color="Coin",
        text=df["Price_USD"].apply(lambda x: f"${x:,.2f}"),
        title="Giá Real-Time Từng Giây (Thang đo Log Scale)",
    )

    fig.update_traces(
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Giá: $%{y:,.2f}<extra></extra>",
    )

    fig.update_layout(
        template="plotly_dark",
        plot_bgcolor="#1E1E1E",
        paper_bgcolor="#121212",
        margin=dict(l=40, r=40, t=50, b=40),
        yaxis=dict(
            type="log",
            title="Giá USD ($)",
            showgrid=True,
            gridcolor="#333333",
            autorange=True,
        ),
        xaxis=dict(title=""),
        showlegend=False,
    )

    status = f"🔴 WebSocket LIVE — Thời gian cập nhật: {now_str}"
    return fig, status

if __name__ == "__main__":
    # Đã cập nhật thành app.run() để không bị lỗi ở Dash phiên bản mới
    app.run(port=8050, debug=False)
