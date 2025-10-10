import pygame
import os


class Player:
    def __init__(self, img, x, ground_y, controllable=False, gravity=0.6, width = 900, height=420, ground_height=40):
        self.image = img
        self.rect = self.image.get_rect(midbottom=(x, ground_y))
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.controllable = controllable
        self.gravity =gravity
        self.ground_height = ground_height
        self.width = width
        self.height = height

    def update(self, keys):
        if self.controllable:
            left = keys[pygame.K_LEFT] or keys[pygame.K_a]
            right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
            jump = keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]

            self.vx = -5 if left and not right else 5 if right and not left else 0
            if jump and self.on_ground:
                self.vy = -12
                self.on_ground = False

        self.vy += self.gravity
        self.rect.x += int(self.vx)
        self.rect.y += int(self.vy)

        ground_y = self.height - self.ground_height
        if self.rect.bottom >= ground_y:
            self.rect.bottom = ground_y
            self.vy = 0
            self.on_ground = True

        self.rect.left = max(0, self.rect.left)
        self.rect.right = min(self.width, self.rect.right)