import os
import sys
import time
import random
import pygame

from ball import Ball
from player import Player

WIDTH, HEIGHT = 900, 420
FPS = 60
GAME_SECONDS = 60
GROUND_HEIGHT = 40
GRAVITY = 0.6
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")


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


def start_screen(screen):
    clock = pygame.time.Clock()
    btn = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50)
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN: return
            if e.type == pygame.MOUSEBUTTONDOWN and btn.collidepoint(e.pos): return
        screen.fill((180,230,255))
        draw_text(screen, "Simple Football", 48, WIDTH//2, HEIGHT//2 - 40)
        pygame.draw.rect(screen, (50,150,50), btn)
        draw_text(screen, "Start Playing", 28, btn.centerx, btn.centery, (255,255,255))
        pygame.display.flip()
        clock.tick(FPS)


def game_over(screen, left_score, right_score):
    clock = pygame.time.Clock()
    if left_score > right_score: msg = "You Win 🏆"
    elif left_score < right_score: msg = "You Lose 😢"
    else: msg = "Draw 🤝"
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT: pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_r: return
            if e.type == pygame.KEYDOWN and e.key == pygame.K_q: pygame.quit(); sys.exit()
        screen.fill((230,230,230))
        draw_text(screen, "Game Over", 50, WIDTH//2, HEIGHT//2 - 80)
        draw_text(screen, msg, 40, WIDTH//2, HEIGHT//2 - 20)
        draw_text(screen, "Press R to replay or Q to quit", 26, WIDTH//2, HEIGHT//2 + 40)
        pygame.display.flip()
        clock.tick(FPS)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Football Frontend Prototype")
    clock = pygame.time.Clock()

    p_left = load_image("player_left.png")
    p_right = load_image("player_right.png")
    ball_img = load_image("ball.png", (30, 30))
    goal_left = load_image("goal_left.png", (22, 140))
    goal_right = load_image("goal_right.png", (22, 140))

    # collison rectangle for the goal bar.
    g_left_rect = goal_left.get_rect(midleft=(0, HEIGHT - GROUND_HEIGHT - goal_left.get_height()//2))
    g_right_rect = goal_right.get_rect(midright=(WIDTH, HEIGHT - GROUND_HEIGHT - goal_right.get_height()//2))

    # Loop controlling restart of the game without restarting the program.
    while True:
        start_screen(screen)
        left = Player(p_left, 110, HEIGHT - GROUND_HEIGHT, controllable=True, gravity = GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)
        right = Player(p_right, WIDTH - 110, HEIGHT - GROUND_HEIGHT, gravity = GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)
        ball = Ball(ball_img, WIDTH//2, HEIGHT//2 - 40, gravity = GRAVITY, width=WIDTH, height=HEIGHT, ground_height=GROUND_HEIGHT)
        lscore = rscore = 0
        start_t = time.time()

        # Game Loop
        while True:
            dt = clock.tick(FPS)/1000
            tleft = GAME_SECONDS - int(time.time() - start_t)
            if tleft <= 0: break

            for e in pygame.event.get():
                if e.type == pygame.QUIT: pass

            keys = pygame.key.get_pressed()
            left.update(keys)
            right.update(keys)
            ball.update([left, right])

            if ball.rect.colliderect(g_right_rect): lscore += 1; ball.reset()
            if ball.rect.colliderect(g_left_rect): rscore += 1; ball.reset()
            

            screen.fill((150,220,255))
            pygame.draw.rect(screen, (60,180,60), (0, HEIGHT - GROUND_HEIGHT, WIDTH, GROUND_HEIGHT))
            screen.blit(goal_left, g_left_rect)
            screen.blit(goal_right, g_right_rect)
            screen.blit(left.image, left.rect)
            screen.blit(right.image, right.rect)
            screen.blit(ball.image, ball.rect)
            draw_text(screen, f"{tleft}s", 26, WIDTH//2, 20)
            draw_text(screen, f"{lscore} - {rscore}", 32, WIDTH//2, 50)
            pygame.display.flip()

        game_over(screen, lscore, rscore)



if __name__ == "__main__":
    main()