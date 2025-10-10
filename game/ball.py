import pygame
import random
import os


class Ball:
    def __init__(self, img, x, y, gravity=0.6, width = 900, height=420, ground_height=40):
        self.image = img
        self.rect = self.image.get_rect(center=(x, y))
        self.radius = self.rect.width // 2
        self.vx = random.choice([-4, 4])
        self.vy = -4

        # Global variables
        self.gravity =gravity
        self.ground_height = ground_height
        self.width = width
        self.height = height

    def reset(self):
        self.rect.center = (self.width // 2, self.height // 2 - 50)
        self.vx = random.choice([-4, 4])
        self.vy = -4

    def update(self, players):
        self.vy += self.gravity
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)

        ground_y = self.height - self.ground_height
        if self.rect.bottom >= ground_y:
            self.rect.bottom = ground_y
            self.vy = -abs(self.vy) * 0.7
            if abs(self.vy) < 1:
                self.vy = 0
            self.vx *= 0.995

        if self.rect.left <= 0 or self.rect.right >= self.width:
            self.vx = -self.vx * 0.8
            self.rect.left = max(self.rect.left, 0)
            self.rect.right = min(self.rect.right, self.width)

        # for p in players:
        #     if self.rect.colliderect(p.rect):
        #         self.vx = self.vx * 0.25 + p.vx * 0.9 + random.uniform(-1, 1)
        #         self.vy = -8 + p.vy * 0.2

        # Circle Collision
        for p in players:
            if self.rect.colliderect(p.rect):
                # approximate circle collision
                ball_center = pygame.Vector2(self.rect.center)
                player_center = pygame.Vector2(p.rect.center)
                diff = ball_center - player_center
                if diff.length() == 0:
                    diff = pygame.Vector2(random.uniform(-1, 1), -1)
                normal = diff.normalize()
                self.vx, self.vy = normal.x * 8, normal.y * 16  # reflect outwards
                self.rect.center += normal * (self.radius + 5)  # push slightly out
