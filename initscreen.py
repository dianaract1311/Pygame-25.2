import pygame
from os import path
import os

pygame.init()

# ----- Gera tela principal
WIDTH = 1100
HEIGHT = 800
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Hello World!')

game = True

image = pygame.image.load('assets/img/background.jpg').convert()
image = pygame.transform.scale(image, (WIDTH, HEIGHT)) 

while game:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game = False

    window.fill((0, 0, 0))
    window.blit(image, (0, 0))

    pygame.display.update()

pygame.quit()