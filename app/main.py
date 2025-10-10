import os
import sys
import time
import random
import pygame
import uuid

from ball import Ball
from connect import WSClient
from player import Player

WIDTH, HEIGHT = 900, 420
FPS = 60
GAME_SECONDS = 60
GROUND_HEIGHT = 40
GRAVITY = 0.6
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
CLIENT_ID = str(uuid.uuid4())

last_sent = 0
SEND_INTERVAL = 0.01  # seconds (100 frames per seconds)


def load_image(name, fallback_size=(50, 90)):
    path = os.path.join(ASSETS_DIR, name)
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception as e:
        print(f"[WARN] {e}. Placeholder used for {name}")
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        surf.fill((200, 80, 80))
        return surf

def draw_text(surf, txt, size, x, y, color=(0,0,0)):
    font = pygame.font.SysFont(None, size)
    img = font.render(txt, True, color)
    rect = img.get_rect(center=(x, y))
    surf.blit(img, rect)


def start_screen(screen, wsclient):
    clock = pygame.time.Clock()
    btn = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50)
    searching = False
    searching_text = "Press Enter or Start to find opponent"
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN:
                # user clicked start; send find_game if ws connected
                if wsclient.connected:
                    wsclient.send({"action": "find_game", "payload": {"client_id": CLIENT_ID}})
                    searching = True
                else:
                    searching_text = "Not connected to server..."
            if e.type == pygame.MOUSEBUTTONDOWN and btn.collidepoint(e.pos):
                if wsclient.connected:
                    wsclient.send({"action": "find_game", "payload": {"client_id": CLIENT_ID}})
                    searching = True
                else:
                    searching_text = "Not connected to server..."

        # handle incoming messages while on start screen
        while wsclient.incoming:
            msg = wsclient.incoming.pop(0)
            if msg.get("type") == "searching":
                searching = True
            if msg.get("type") == "matched":
                # got matched: return and start game
                wsclient.in_game = True
                wsclient.game_id = msg.get("game_id")
                wsclient.role = msg.get("role")
                return  # start actual game
        screen.fill((180,230,255))
        draw_text(screen, "Simple Football", 48, WIDTH//2, HEIGHT//2 - 40)
        pygame.draw.rect(screen, (50,150,50), btn)
        draw_text(screen, "Start Playing", 28, btn.centerx, btn.centery, (255,255,255))
        if searching:
            draw_text(screen, "Searching opponent...", 22, WIDTH//2, HEIGHT//2 + 120)
        else:
            draw_text(screen, searching_text, 18, WIDTH//2, HEIGHT//2 + 120)
        pygame.display.flip()
        clock.tick(FPS)


def game_over(screen, left_score, right_score, my_role):
    clock = pygame.time.Clock()
    # Determine win/loss based on player's role
    if my_role == "left":
        if left_score > right_score: 
            msg = "You Win 🏆"
        elif left_score < right_score: 
            msg = "You Lose 😢"
        else: 
            msg = "Draw 🤝"
    else:  # my_role == "right"
        if right_score > left_score: 
            msg = "You Win 🏆"
        elif right_score < left_score: 
            msg = "You Lose 😢"
        else: 
            msg = "Draw 🤝"
    
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r: return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q: pygame.quit(); sys.exit()
        screen.fill((230,230,230))
        draw_text(screen, "Game Over", 50, WIDTH//2, HEIGHT//2 - 80)
        draw_text(screen, msg, 40, WIDTH//2, HEIGHT//2 - 20)
        draw_text(screen, f"Final Score: {left_score} - {right_score}", 30, WIDTH//2, HEIGHT//2 + 20)
        draw_text(screen, "Press R to replay or Q to quit", 26, WIDTH//2, HEIGHT//2 + 60)
        pygame.display.flip()
        clock.tick(FPS)


def main():
    # Initialize pygame
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Football Multiplayer")
    clock = pygame.time.Clock()

    # Create and start websocket client
    ws = WSClient("ws://0.0.0.0:3005/ws/game/")
    ws.start()

    # Wait on start screen until match found
    start_screen(screen, ws)

    # Matched: setup assets
    print("Matched! Starting game...")
    p_left = load_image("player_left.png")
    p_right = load_image("player_right.png")
    ball_img = load_image("ball.png", (30, 30))
    goal_left = load_image("goal_left.png", (22, 140))
    goal_right = load_image("goal_right.png", (22, 140))

    g_left_rect = goal_left.get_rect(midleft=(0, HEIGHT - GROUND_HEIGHT - goal_left.get_height() // 2))
    g_right_rect = goal_right.get_rect(midright=(WIDTH, HEIGHT - GROUND_HEIGHT - goal_right.get_height() // 2))

    # Assign controllable players based on role
    left = Player(p_left, 110, HEIGHT - GROUND_HEIGHT, controllable=(ws.role == "left"),
                  gravity=GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)
    right = Player(p_right, WIDTH - 110, HEIGHT - GROUND_HEIGHT, controllable=(ws.role == "right"),
                   gravity=GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)
    ball = Ball(ball_img, WIDTH // 2, HEIGHT // 2 - 40,
                gravity=GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)

    lscore = rscore = 0
    start_t = time.time()
    last_sent = 0
    SEND_INTERVAL = 0.05  # smoother network updates

    # Chat input
    chat_input = ""
    chat_messages = []
    chat_active = False  # Chat is inactive by default

    running = True
    while running:
        dt = clock.tick(FPS) / 1000
        tleft = GAME_SECONDS - int(time.time() - start_t)

        # Handle Events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                ws.send({"action": "leave_game", "payload": {"player_id": ws.client_id}})
                ws.stop()
                pygame.quit()
                sys.exit()
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SLASH:
                    # Toggle chat mode
                    chat_active = not chat_active
                    if not chat_active:
                        chat_input = ""  # Clear input when closing chat
                elif chat_active:
                    # Only handle chat input when chat is active
                    if e.key == pygame.K_RETURN:
                        if chat_input.strip():
                            ws.send({
                                "action": "chat",
                                "payload": {"player_id": ws.client_id, "message": chat_input}
                            })
                            chat_input = ""
                        chat_active = False  # Close chat after sending
                    elif e.key == pygame.K_BACKSPACE:
                        chat_input = chat_input[:-1]
                    elif e.key == pygame.K_ESCAPE:
                        chat_input = ""
                        chat_active = False
                    else:
                        # Only accept printable ASCII characters
                        if e.unicode.isprintable() and e.key != pygame.K_SLASH:
                            chat_input += e.unicode
                else:
                    # Game controls only when chat is not active
                    if e.key == pygame.K_q:
                        running = False
                        ws.send({"action": "leave_game", "payload": {"player_id": ws.client_id}})

        # Update controllable player (only when chat is not active)
        if not chat_active:
            keys = pygame.key.get_pressed()
            if ws.role == "left":
                left.update(keys)
            else:
                right.update(keys)

        # Ball collision logic (local)
        ball.update([left, right])

        # Goal detection
        if ball.rect.colliderect(g_left_rect):
            rscore += 1
            ws.send({
                "action": "score",
                "payload": {"left": lscore, "right": rscore}
            })
            ball.reset()
        elif ball.rect.colliderect(g_right_rect):
            lscore += 1
            ws.send({
                "action": "score",
                "payload": {"left": lscore, "right": rscore}
            })
            ball.reset()

        # Send updates to server
        now = time.time()
        if ws.in_game and now - last_sent > SEND_INTERVAL:
            last_sent = now
            my_player = left if ws.role == "left" else right
            ws.send({
                "action": "update",
                "payload": {
                    "player_id": ws.client_id,
                    "pos": {"x": my_player.rect.x, "y": my_player.rect.y},
                    "vx": my_player.vx,
                    "vy": my_player.vy,
                    "ball": {
                        "x": ball.rect.centerx,
                        "y": ball.rect.centery,
                        "vx": ball.vx,
                        "vy": ball.vy,
                    },
                }
            })

        # Process incoming messages
        while ws.incoming:
            msg = ws.incoming.pop(0)
            t = msg.get("type")

            if t == "update":
                payload = msg.get("payload", {})
                from_id = msg.get("from")
                
                # Don't update own player from network
                if from_id == ws.client_id:
                    continue

                # Update opponent's position
                opponent = right if ws.role == "left" else left
                pos = payload.get("pos")
                if pos:
                    opponent.rect.x = int(pos.get("x", opponent.rect.x))
                    opponent.rect.y = int(pos.get("y", opponent.rect.y))
                
                # Update opponent's velocity
                if "vx" in payload:
                    opponent.vx = float(payload.get("vx", opponent.vx))
                if "vy" in payload:
                    opponent.vy = float(payload.get("vy", opponent.vy))

                # Sync ball
                ball_data = payload.get("ball")
                if ball_data:
                    ball.rect.centerx = int(ball_data.get("x", ball.rect.centerx))
                    ball.rect.centery = int(ball_data.get("y", ball.rect.centery))
                    ball.vx = float(ball_data.get("vx", ball.vx))
                    ball.vy = float(ball_data.get("vy", ball.vy))

            elif t == "score_update":
                payload = msg.get("payload", {})
                if "left" in payload:
                    lscore = int(payload.get("left", lscore))
                if "right" in payload:
                    rscore = int(payload.get("right", rscore))

            elif t == "chat":
                chat_payload = msg.get("payload", {})
                message = chat_payload.get("message", "")
                player_id = chat_payload.get("player_id", "")
                
                # Show who sent the message
                if player_id == ws.client_id:
                    display_msg = f"You: {message}"
                else:
                    display_msg = f"Opponent: {message}"
                
                chat_messages.append(display_msg)
                # Keep only last 5 messages
                if len(chat_messages) > 5:
                    chat_messages.pop(0)

            elif t == "player_left":
                draw_text(screen, "Opponent Left the Game", 30, WIDTH // 2, HEIGHT // 2)
                pygame.display.flip()
                ws.opponent_connected = False
                time.sleep(2)
                running = False

        # End game if timer finished
        if tleft <= 0:
            running = False

        # Draw everything
        screen.fill((150, 220, 255))
        pygame.draw.rect(screen, (60, 180, 60),
                         (0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT))
        screen.blit(goal_left, g_left_rect)
        screen.blit(goal_right, g_right_rect)
        screen.blit(left.image, left.rect)
        screen.blit(right.image, right.rect)
        screen.blit(ball.image, ball.rect)

        draw_text(screen, f"{tleft}s", 26, WIDTH // 2, 20)
        draw_text(screen, f"{lscore} - {rscore}", 32, WIDTH // 2, 50)

        # Chat display
        y = HEIGHT - GROUND_HEIGHT - 20
        for msg in chat_messages:
            draw_text(screen, msg, 18, WIDTH // 2, y, (255, 255, 255))
            y -= 20
        
        # Show chat input when active
        if chat_active:
            chat_box_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT - 30, 400, 25)
            pygame.draw.rect(screen, (255, 255, 255), chat_box_rect)
            pygame.draw.rect(screen, (0, 0, 0), chat_box_rect, 2)
            draw_text(screen, chat_input + "_", 18, WIDTH // 2, HEIGHT - 17, (0, 0, 0))
        else:
            # Show instruction to open chat
            draw_text(screen, "Press / to chat", 16, WIDTH // 2, HEIGHT - 15, (200, 200, 200))

        pygame.display.flip()

    # Game Over - pass role to determine winner correctly
    game_over(screen, lscore, rscore, ws.role)
    ws.stop()

if __name__ == "__main__":
    main()