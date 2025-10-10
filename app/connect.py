import websocket
import threading
import json
import uuid
import time

CLIENT_ID = str(uuid.uuid4())

class WSClient:
    def __init__(self, url):
        self.url = url
        self.ws = None
        self.connected = False
        self.client_id = None  # server assigned
        self.in_game = False
        self.game_id = None
        self.role = None
        self.opponent_connected = False
        self.incoming = []
        self.stop_flag = False

    def start(self):
        def run():
            while not self.stop_flag:
                try:
                    self.ws = websocket.WebSocketApp(
                        self.url,
                        on_open=self.on_open,
                        on_message=self.on_message,
                        on_close=self.on_close,
                        on_error=self.on_error
                    )
                    self.ws.run_forever(ping_interval=20, ping_timeout=10)
                except Exception as e:
                    print("WS thread error:", e)
                time.sleep(1)
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def on_open(self, ws):
        self.connected = True
        # Do not auto-join matchmaking here; let UI send find_game when user presses start.

    def on_message(self, ws, message):
        try:
            data = json.loads(message)
        except:
            return
        # if server assigns client id, capture it
        if data.get("type") == "connected" and data.get("client_id"):
            self.client_id = data["client_id"]
        self.incoming.append(data)

    def on_close(self, ws, status, msg):
        self.connected = False
        self.incoming.append({"type": "ws_closed"})

    def on_error(self, ws, error):
        print("WS error", error)

    def send(self, data):
        try:
            if self.ws and self.connected:
                self.ws.send(json.dumps(data))
        except Exception as e:
            print("WS send error:", e)

    def stop(self):
        self.stop_flag = True
        try:
            if self.ws:
                self.ws.close()
        except:
            pass
