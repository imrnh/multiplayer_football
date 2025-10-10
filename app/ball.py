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
        self.gravity = gravity
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

        # Circle Collision - From leg to head
        for p in players:
            # Create collision hitbox from bottom (leg) to top (head)
            # Use full player rect for collision detection
            player_hitbox = p.rect.copy()
            
            # Expand hitbox slightly downward to ensure leg collision
            player_hitbox.height += 10  # Add 10px below for better leg detection
            player_hitbox.y -= 10  # Move up so bottom stays at same position
            
            if self.rect.colliderect(player_hitbox):
                ball_center = pygame.Vector2(self.rect.center)
                player_center = pygame.Vector2(p.rect.center)
                diff = ball_center - player_center
                
                if diff.length() == 0:
                    diff = pygame.Vector2(random.uniform(-1, 1), -1)
                
                normal = diff.normalize()
                
                # Apply force based on collision
                self.vx, self.vy = normal.x * 8, normal.y * 16
                
                # Push ball out to prevent sticking
                self.rect.center += normal * (self.radius + 5)