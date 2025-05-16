import threading
import logging
import random
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import deque

from src.algorithm.models import shared_data
from src.algorithm.models.shared_data import SharedData
from src.algorithm.models.trade_signals import SIGNAL



class Dashboard:
    
    def __init__(self, shared_data: SharedData, port: int= 8050):
        self.shared_data = shared_data
        self.port = port
        self.ltpc_data_rolling_window = deque(maxlen=100) 
        self.app = dash.Dash(__name__)
        self._setup_layout()
        self._setup_callbacks()


    def _setup_layout(self):
        
        # self.app.layout = html.Div([
        #     html.H2("Interactive Real-Time Stock Chart"),
        #     dcc.Graph(id="live-chart"),
        #     dcc.Interval(id="interval-component", interval=5*1000, n_intervals=0)
        # ])
        self.app.layout = html.Div(
            children=[
                dcc.Graph(
                    id="live-chart",
                    style={
                        "width": "100%",
                        "height": "100%"
                    }
                ),
                dcc.Interval(id="interval-component", interval=1*1000, n_intervals=0)
            ],
            style={
                "width": "100vw",
                "height": "100vh",
                "margin": 0,
                "padding": 0
            }
        )
    
    def _setup_callbacks(self):
        @self.app.callback(
            Output("live-chart", "figure"),
            Input("interval-component", "n_intervals")
        )
        
        def update_chart(n):
            
            
            # color-setup:
            ema9_color = "yellow"
            ema20_color = "blue"
            vwap_color = "brown"
            
            # Tick Data plotting:
            self.ltpc_data_rolling_window.extend(self.shared_data.ltpc_data_window)
            self.shared_data.ltpc_data_window.clear()
            
            # if not self.ltpc_data_rolling_window:
                # return dash.no_update
            
            timestamps = [tick.ltt for tick in self.ltpc_data_rolling_window]
            prices = [tick.ltp for tick in self.ltpc_data_rolling_window]
            
            candles = None
            if self.shared_data.one_min_candles:
                candles = self.shared_data.one_min_candles  
            elif self.shared_data.five_min_candles:
                candles = self.shared_data.five_min_candles

            # candles = five_min_candles
            ema9_hist = self.shared_data.ema9
            ema20_hist = self.shared_data.ema20
            vwap_hist = self.shared_data.vwap
            trade_signals = self.shared_data.trade_signals

            # Save Profit booking levels:
            profit_levels = []
            
            fig = make_subplots(
                
                rows=2, cols=1,
                shared_xaxes=False,
                row_heights=[0.8, 0.2],
                vertical_spacing=0.2,
                specs=[
                    [{"type": "candlestick"}],
                    [{"type": "bar"}]
                ],
                subplot_titles=[
                    "Indicators",
                    "Volume"
                ],
            )
            
            # fig = go.Figure()
            
            if self.ltpc_data_rolling_window:
                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=prices,
                        mode="lines+markers",
                        line=dict(color='cyan', width=1),
                        name="LTP (Tick Data)",
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Bar(
                            x=timestamps,
                            y=[tick.ltq for tick in self.ltpc_data_rolling_window],
                            name="Volume",
                            marker_color="magenta",
                            width=5,
                            yaxis="y2"
                        ),
                        row=2, col=1
                )
                fig.update_layout(
                    title = "Tick-By-Tick Chart Data",
                    xaxis_title = "Time",
                    template="plotly_dark",
                    yaxis=dict(
                        title="Price",
                        side="right",
                        showgrid=False,
                    ),
                    yaxis2=dict(
                        title="Volume",
                        side="left",
                        showgrid=False,
                        position=1.0
                    ),
                    xaxis_rangeslider_visible=False,
                    
                )
            elif not candles:
                dash.no_update 
            elif candles:
                fig.add_trace(
                    go.Candlestick(
                        x = [c.timestamp for c in candles],
                        open=[c.open for c in candles],
                        high=[c.high for c in candles],
                        low=[c.low for c in candles],
                        close=[c.close for c in candles],
                        name="Price",
                        opacity=0.4,
                    ),
                    row=1, col=1
                )
                
                # EMA 9 trace
                if ema9_hist:
                    fig.add_trace(
                        go.Scatter(
                            x=[e.timestamp for e in ema9_hist],
                            y=[e.value for e in ema9_hist],
                            mode="lines",
                            line=dict(color=ema9_color, width=1),
                            name="9 EMA"
                        ),
                        row=1, col=1
                    )
                    
                # EMA 20 trace
                if ema20_hist:
                    fig.add_trace(
                        go.Scatter(
                            x=[e.timestamp for e in ema20_hist],
                            y=[e.value for e in ema20_hist],
                            mode="lines",
                            line=dict(color=ema20_color, width=1),
                            name="20 EMA"
                        ),
                        row=1, col=1
                    )
                    
                # VWAP trace
                if vwap_hist:
                    fig.add_trace(
                        go.Scatter(
                            x=[v.timestamp for v in vwap_hist],
                            y=[v.value for v in vwap_hist],
                            mode="lines",
                            line=dict(color=vwap_color, width=1),
                            name="VWAP"
                        ),
                        row=1, col=1
                    )
                
                # Volume trace
                volumes = [c.volume for c in candles if c.volume is not None]
                if volumes:
                    fig.add_trace(
                        go.Bar(
                            x=[c.timestamp for c in candles if c.volume is not None],
                            y=volumes,
                            name="Volume",
                            marker_color="magenta",
                            opacity=0.4,
                            yaxis="y2"
                        ),
                        row=2, col=1
                    )  
                    fig.add_trace(
                        go.Scatter(
                            x=[c.timestamp for c in candles if c.volume is not None],
                            y=volumes,
                            mode="lines",
                            line=dict(color="magenta" , width=1),
                            yaxis="y2"
                        ),
                        row=2, col=1
                    )
                    
                if trade_signals:
                    signal_colors = {"WAIT": "gray", "BUY": "green", "HOLD": "blue", "SELL": "red"}
                    signal_shapes = {"WAIT": "circle", "BUY": "triangle-up", "HOLD": "square", "SELL": "triangle-down"}
                    
                    for signal in trade_signals:
                        if signal.signal == "BUY" or signal.signal=="SELL":
                        # if True:    
                            fig.add_trace(
                                go.Scatter(
                                    x = [signal.timestamp],
                                    y=[signal.value],
                                    mode =  "markers+text",
                                    marker = dict(
                                        color=signal_colors[signal.signal],
                                        symbol=signal_shapes[signal.signal],
                                        size=15
                                    ),
                                    text=signal.signal,
                                    textposition="top center",
                                    name=signal.signal,
                                    showlegend=False
                                ),
                                row=1, col=1
                            )
                            if signal.signal == "BUY":
                                profit_levels = []
                            
                            if signal.signal == "SELL":
                                
                                colors = ["green", "purple", "orange", "cyan", "pink", "white", "purple"]
                                if len(profit_levels) != 0:
                                    for level_data in profit_levels:
                                        level_num = level_data["level"]
                                        tn = level_data["value"]
                                        start_time = level_data["timestamp"]
                                        color = colors[level_num % len(colors)]
                                        
                                        fig.add_trace(
                                            go.Scatter(
                                                x = [start_time, signal.timestamp],
                                                y = [tn, tn],
                                                mode = "lines",
                                                line = dict(color= color, width=1, dash='dot'),
                                                name = f"T:({level_num})",
                                                showlegend=False
                                            ),
                                            row=1, col=1
                                        )
                                        
                            
                        if signal.signal == "HOLD":
                            if len(signal.levels) != 0:
                                profit_levels = list(
                                    {entry["value"]: entry for entry in signal.levels}.values()
                                )
                            
                                    
                                # profit_levels.append(signal.levels)
                                    
                                # for level_data in signal.levels:
                                #     level_num = level_data["level"]
                                #     tn = level_data["value"]
                                #     start_time = level_data["timestamp"]
                                #     color = f"rgb({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)})"
                                    
                                #     fig.add_shape(
                                #         type = "line",
                                #         x0 = start_time, x1=signal.timestamp,
                                #         y0 = tn, y1 = tn,
                                #         line= dict(color=color, width=1, dash="dot")
                                #     )
                                    

                fig.update_layout(
                    title = "Real-Time Chart",
                    xaxis2_title = "Time",
                    # xaxis_title = "Time",
                    template="plotly_dark",
                    yaxis=dict(
                        title="Price",
                        side="right",
                        showgrid=False,
                    ),
                    yaxis2=dict(
                        title="Volume",
                        side="left",
                        showgrid=False,
                        position=1.0
                    ),
                    xaxis_rangeslider_visible=False
                )
                
                fig.update_xaxes(
                    rangebreaks = [
                        dict(bounds=['sat', 'mon']),
                        dict(bounds=[15.5, 9.25], pattern="hour")
                    ]
                ) 
            
            return fig
    
    def invoke(self):
        
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        logging.getLogger('dash').setLevel(logging.CRITICAL)
        self.app.run(debug=False, port=self.port)
        # self.app.run(debug=False, host="192.168.0.111", port=self.port)


def start_dashboard(shared_data: SharedData, port: int = 8050):
    dashboard = Dashboard(shared_data, port)
    dashboard.invoke()

def run_dashboard_in_thread(shared_data: SharedData, port: int = 8050):
    dash_thread = threading.Thread(
        target=start_dashboard,
        args=(shared_data, port),
        daemon=True,
    )
    
    dash_thread.start()
    return dash_thread