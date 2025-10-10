import asyncio
import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
import redis.asyncio as aioredis

REDIS_URL = "redis://127.0.0.1:6379/0"
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

WAITING_QUEUE_KEY = "waiting_players"

def _game_state_key(game_id):
    return f"game:{game_id}:state"

def _game_players_key(game_id):
    return f"game:{game_id}:players"

# Physics constants
GRAVITY = 0.6
GROUND_Y = 420 - 40
WIDTH = 900
HEIGHT = 420
FRICTION = 0.995
BALL_RADIUS = 15

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.client_id = str(uuid.uuid4())
        self.game_id = None
        self.role = None
        await self.accept()
        await self.channel_layer.group_add(f"player_{self.client_id}", self.channel_name)
        await self.send_json({"type": "connected", "client_id": self.client_id})

    async def disconnect(self, code):
        if self.game_id:
            await redis.hset(_game_state_key(self.game_id), f"player:{self.client_id}:connected", "0")
            await self.channel_layer.group_send(
                self.game_group_name,
                {"type": "player.left", "client_id": self.client_id}
            )
        queue_players = await redis.lrange(WAITING_QUEUE_KEY, 0, -1)
        if self.client_id in queue_players:
            await redis.lrem(WAITING_QUEUE_KEY, 0, self.client_id)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        action = data.get("action")
        if action == "find_game":
            await self.find_match()
        elif action == "leave_game":
            await self.leave_game()
        elif action == "update":
            await self.handle_update(data.get("payload", {}))
        elif action == "chat":
            await self.handle_chat(data.get("payload", {}))
        elif action == "score":
            await self.handle_score(data.get("payload", {}))

    # Matchmaking
    async def find_match(self):
        await redis.rpush(WAITING_QUEUE_KEY, self.client_id)
        queue_len = await redis.llen(WAITING_QUEUE_KEY)
        if queue_len >= 2:
            p1 = await redis.lpop(WAITING_QUEUE_KEY)
            p2 = await redis.lpop(WAITING_QUEUE_KEY)
            if self.client_id not in (p1, p2):
                await redis.lpush(WAITING_QUEUE_KEY, p2, p1)
                await self.send_json({"type": "searching"})
                return

            other = p1 if p2 == self.client_id else p2
            game_id = str(uuid.uuid4())
            role_map = {self.client_id: "left", other: "right"}

            # Initial game state
            initial_state = {
                "ball_x": str(WIDTH // 2),
                "ball_y": str(HEIGHT // 2 - 50),
                "ball_vx": str(4),
                "ball_vy": str(-4),
                "score_left": "0",
                "score_right": "0",
                f"player:{self.client_id}:role": role_map[self.client_id],
                f"player:{self.client_id}:connected": "1",
                f"player:{other}:role": role_map[other],
                f"player:{other}:connected": "1",
                f"player:{p1}:x": "110",
                f"player:{p2}:x": str(WIDTH-110),
                f"player:{p1}:y": str(GROUND_Y),
                f"player:{p2}:y": str(GROUND_Y)
            }
            await redis.hset(_game_state_key(game_id), mapping=initial_state)
            await redis.sadd(_game_players_key(game_id), self.client_id, other)

            # Setup consumer state
            self.game_id = game_id
            self.role = role_map[self.client_id]
            self.game_group_name = f"game_{game_id}"
            await self.channel_layer.group_add(self.game_group_name, self.channel_name)

            # Notify both players via their private groups
            for player_id in [self.client_id, other]:
                await self.channel_layer.group_send(
                    f"player_{player_id}",
                    {
                        "type": "matched",
                        "game_id": game_id,
                        "role": role_map[player_id],
                        "state": initial_state
                    }
                )
        else:
            await self.send_json({"type": "searching"})

    # Player updates
    async def handle_update(self, payload):
        if not self.game_id:
            return

        state_key = _game_state_key(self.game_id)
        mapping = {}
        player_id = payload.get("player_id", self.client_id)

        pos = payload.get("pos")
        if pos:
            mapping[f"player:{player_id}:x"] = str(pos.get("x", 0))
            mapping[f"player:{player_id}:y"] = str(pos.get("y", 0))
        if "vx" in payload:
            mapping[f"player:{player_id}:vx"] = str(payload.get("vx"))
        if "vy" in payload:
            mapping[f"player:{player_id}:vy"] = str(payload.get("vy"))
        if "ball" in payload:
            ball = payload["ball"]
            mapping["ball_x"] = str(ball.get("x", 0))
            mapping["ball_y"] = str(ball.get("y", 0))
            mapping["ball_vx"] = str(ball.get("vx", 0))
            mapping["ball_vy"] = str(ball.get("vy", 0))

        if mapping:
            await redis.hset(state_key, mapping=mapping)

        # Broadcast to both players (including sender for confirmation)
        await self.channel_layer.group_send(
            f"game_{self.game_id}",
            {
                "type": "game.update",
                "payload": payload,
                "from": player_id,
            }
        )

    # Score updates
    async def handle_score(self, payload):
        if not self.game_id:
            return
        
        state_key = _game_state_key(self.game_id)
        mapping = {}
        if "left" in payload:
            mapping["score_left"] = str(payload["left"])
        if "right" in payload:
            mapping["score_right"] = str(payload["right"])
        
        if mapping:
            await redis.hset(state_key, mapping=mapping)
        
        # Broadcast score update to both players
        await self.channel_layer.group_send(
            f"game_{self.game_id}",
            {
                "type": "score.update",
                "payload": payload,
                "from": self.client_id,
            }
        )

    # Chat
    async def handle_chat(self, payload):
        if not self.game_id:
            return
        message = payload.get("message", "")
        player_id = payload.get("player_id", self.client_id)
        
        # Broadcast to both players in the game
        await self.channel_layer.group_send(
            self.game_group_name,
            {
                "type": "chat.message",
                "payload": {"player_id": player_id, "message": message}
            }
        )

    async def chat_message(self, event):
        await self.send_json({"type": "chat", "payload": event["payload"]})

    # Leave / matched / player_left
    async def leave_game(self):
        if not self.game_id:
            return
        await redis.hset(_game_state_key(self.game_id), f"player:{self.client_id}:connected", "0")
        await self.channel_layer.group_send(
            self.game_group_name,
            {"type": "player.left", "client_id": self.client_id}
        )

    async def matched(self, event):
        await self.send_json({
            "type": "matched",
            "game_id": event["game_id"],
            "role": event["role"],
            "state": event["state"]
        })
        self.game_id = event["game_id"]
        self.game_group_name = f"game_{self.game_id}"
        await self.channel_layer.group_add(self.game_group_name, self.channel_name)

    async def player_left(self, event):
        await self.send_json({"type": "player_left", "client_id": event["client_id"]})

    async def game_update(self, event):
        await self.send_json({"type": "update", "payload": event["payload"], "from": event.get("from")})

    async def score_update(self, event):
        await self.send_json({"type": "score_update", "payload": event["payload"], "from": event.get("from")})

    async def send_json(self, data):
        await self.send(text_data=json.dumps(data))