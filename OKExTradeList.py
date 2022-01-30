
import json
import datetime
import pytz
import threading
import websocket # ! Make sure to pip install websocket-client!
import pandas as pd
import ssl

import dash
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output


## * Settings ######################################

SWAP_IDS = ["BTC-USDT-SWAP", "ETH-USDT-SWAP"]

uri_public_ws = "wss://ws.okx.com:8443/ws/v5/public"

exch = "OKEx"
update_time = 100
MAX_LENGTH = 200
DASH_PORT = 9093

HEADER_TITLE = "Trade List"

FONTSIZE_HEADER = 12
FONTSIZE_COLUMNS = 10
FONTSIZE_TEXT = 10

Colours = {
    "HeaderBg": "rgb(194,214,220)",
    "HeaderText": "rgb(0,0,0)",
    "ColumnBg": "rgb(255,255,255)",
    "ColumnText": "rgb(100,100,100)",
    "TradeListText": "rgb(255,255,255)",
    "TradeListBg": "rgb(0,0,0)",
    "aggr_bid": "rgb(255,127,41)",
    "aggr_ask": "rgb(74,165,255)",
}


# Order however wanted
widths = {
    "Time": "100px",
    "ID": "200px",
    "Aggr": "40px", 
    "Qty": "40px", 
    "Price": "60px",
}

HEADERS = [i for i in widths]

width_num = sum([int(widths[i][:-2]) + 1 for i in widths])
# 10 = 2 * padding of header
widths["Table"] = str(width_num + 10) + "px"
widths["Header"] = str(width_num)+"px"

# * Cell Styling #########################################################

header_style = {
    "backgroundColor": Colours["HeaderBg"],
    "color": Colours["HeaderText"],
    "fontFamily": "Arial",
    "fontWeight": "bold",
    "textAlign": "center",
    "fontSize": FONTSIZE_HEADER,
    "padding": "5px",
    "width": widths["Header"],
    "minWidth": widths["Header"],
    "maxWidth": widths["Header"],
    'margin-left': '-8px',
    'margin-top' : '-8px'
}

column_header_style = {
    "backgroundColor": Colours["ColumnBg"],
    "color": Colours["ColumnText"],
    "fontFamily": "Arial",
    "fontWeight": "bold",
    "fontSize": FONTSIZE_COLUMNS,
    "padding": "5px",
    "height": "25px",
    "textAlign": "center",
    "border":"1px grey solid",
    "border-top":"1px grey solid",
}

cell_style = {
    "backgroundColor": Colours["TradeListBg"],
    "color": Colours["TradeListText"],
    "fontFamily": "Arial",
    "textAlign": "right",
    "padding": "5px",
    "height": "25px",
    "fontWeight": "bold",
    "border":"1px grey solid",
    "fontSize": FONTSIZE_TEXT,
}


style_cell_conditional=[{
        'if': {'column_id': c},
        "width": widths[c],
        "minWidth": widths[c],
        "maxWidth": widths[c]
    } for c in widths
]

style_cell_conditional += [{
        'if': {'column_id': c},
        "textAlign": "left",
    } for c in ["ID", "Aggr"]
]

style_data_conditional = [
    {
        "if": {"state": "selected"},
                "backgroundColor": "inherit !important",
                "border": "inherit !important",
    }
]

style_data_conditional.append(
    {
    "if": {'filter_query': '{Aggr} = "Bid"', 'column_id': "Aggr"},
            "color": Colours["aggr_bid"],

    }
)
style_data_conditional.append(
    {
    "if": {'filter_query': '{Aggr} = "Ask"', 'column_id': "Aggr"},
            "color": Colours["aggr_ask"],

    }
)

# * ################################################

# Contains the dataframe of each future + rate and delta exposure

df = pd.DataFrame(columns = HEADERS)

def generate_table():
    global df
    return dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df[::-1].to_dict('records'),
        style_header=column_header_style,
        style_table = {'width': widths["Table"], 'overflowY': 'auto', 'margin-left':'-8px'},
        style_cell=cell_style,
        style_cell_conditional = style_cell_conditional,
        style_data_conditional = style_data_conditional,
        css=[
            {"selector": ".dash-spreadsheet tr", "rule": "height: 2px; min-height: 2px; padding: npx; margin: npx"},
            {"selector": ".dash-spreadsheet tr td", "rule": "height: 2px; min-height: 2px; padding: npx; margin: npx"},
            {"selector": ".show-hide", "rule": "display: none"}
        ],
    )

# * #####################################################

# * Order Message Parsing ####################################################

def process_trade_info(x):
    global df
    
    try:

        info = json.loads(x)
        info = info["data"][0]
        time = datetime.datetime.fromtimestamp(int(info["ts"])/1000, pytz.timezone("Europe/London")).strftime('%H:%M:%S.%f')[:-3]
        fut_id = exch+"-"+info["instId"]
        side = info["side"]
        if side == "sell":
            side = "Ask"
        elif side == "buy":
            side = "Bid"
        
        qty = info["sz"]
        price = info["px"]

        my_dict = {"Time": time, "ID": fut_id, "Qty": qty, "Price": price, "Aggr": side}
        df = df.append(my_dict, ignore_index=True)
        df = df.tail(MAX_LENGTH)
    
    except Exception as e:
        print(e)


# * #####################################################

# * Websocket Server #######################################################

def CreateTradesPayload(fut_id):
    return json.dumps({
        "op": "subscribe",
        "args": [
            {
                "channel": "trades",
                "instId": fut_id
            }
        ]
    })

def on_message(ws, message):
    process_trade_info(message)

def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    for SWAP_ID in SWAP_IDS:
        ws.send(CreateTradesPayload(SWAP_ID))

def start_ws_thread():

    ws = websocket.WebSocketApp(uri_public_ws,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.run_forever(ping_interval=60, ping_timeout=10, sslopt={"cert_reqs": ssl.CERT_NONE,
                    "check_hostname": False,
                    "ssl_version": ssl.PROTOCOL_TLSv1})
ws_thread = threading.Thread(target = start_ws_thread, name = "async_ws_thread")
ws_thread.start()


# * ###################################################################

# * ###################################################################

app = dash.Dash(__name__, update_title = None)

app.layout = html.Div([
    html.Div(
        HEADER_TITLE,
        style=header_style
    ),
    html.Div(generate_table(), id = "tableholder"),
    dcc.Interval(
        id='interval-component',
        interval=update_time, # in milliseconds
        n_intervals=0
    )
])

@app.callback(Output('tableholder', 'children'),
              Input('interval-component', 'n_intervals'))
def update_table(n):
    return generate_table()


if __name__ == '__main__':
    app.run_server(port=DASH_PORT)
    # app.run_server(port=DASH_PORT, debug = True) # as you save code it updates
    
