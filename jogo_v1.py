# ===== Inicialização =====
# ----- Importa e inicia pacotes
import pygame
import random

pygame.init()

# ----- Gera tela principal
WIDTH, HEIGHT = 1280, 720
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Jardim Esquecido')

# ----- Limites do mundo 
WORLD_LEFT = 0
WORLD_RIGHT = 5000
WORLD_TOP = 0
WORLD_BOTTOM = 720  # altura total do mundo 
WORLD_LIMITS = (WORLD_LEFT, WORLD_RIGHT, WORLD_TOP, WORLD_BOTTOM)

# ----- Classe da câmera
class Camera:
    def __init__(self, w, h, lerp=0.12, deadzone_w=400, deadzone_h=200, lookahead_x=100):
        self.w = w
        self.h = h
        self.lerp = lerp
        self.x = 0.0
        self.y = 0.0
        self.deadzone_w = deadzone_w
        self.deadzone_h = deadzone_h
        self.lookahead_x = lookahead_x
        self._current_look_x = 0.0
        self._look_smooth = 0.12

    def _lerp(self, a, b, t):
        return a + (b - a) * t

    def update(self, player_rect, player_vx, world_limits):
        left_limit, right_limit, top_limit, bottom_limit = world_limits

        dz_left = self.x + (self.w - self.deadzone_w) * 0.5
        dz_top = self.y + (self.h - self.deadzone_h) * 0.5
        dz_rect = pygame.Rect(int(dz_left), int(dz_top), int(self.deadzone_w), int(self.deadzone_h))

        desired_cx = self.x + self.w / 2
        desired_cy = self.y + self.h / 2

        if player_rect.centerx < dz_rect.left:
            offset = dz_rect.left - player_rect.centerx
            desired_cx -= offset
        elif player_rect.centerx > dz_rect.right:
            offset = player_rect.centerx - dz_rect.right
            desired_cx += offset

        if player_rect.centery < dz_rect.top:
            offset = dz_rect.top - player_rect.centery
            desired_cy -= offset
        elif player_rect.centery > dz_rect.bottom:
            offset = player_rect.centery - dz_rect.bottom
            desired_cy += offset

        # lookahead
        target_look = (1 if player_vx > 0 else -1 if player_vx < 0 else 0) * self.lookahead_x
        self._current_look_x = self._lerp(self._current_look_x, target_look, self._look_smooth)
        desired_cx += self._current_look_x

        desired_x = desired_cx - self.w / 2
        desired_y = desired_cy - self.h / 2

        desired_x = max(left_limit, min(right_limit - self.w, desired_x))
        desired_y = max(top_limit, min(bottom_limit - self.h, desired_y))

        self.x = self._lerp(self.x, desired_x, self.lerp)
        self.y = self._lerp(self.y, desired_y, self.lerp)


# ----- Classe do personagem
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.color = (255, 0, 0)
        self.vx = 0.0
        self.vy = 0.0
        self.speed = 5.0
        self.jump = -15.0
        self.on_ground = True

    def update(self, keys, platforms):
        self.vx = 0.0
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
        if keys[pygame.K_RIGHT]:
            self.vx = self.speed

        # Movimento horizontal
        self.rect.x += int(self.vx)

        # Gravidade
        self.rect.y += int(self.vy)
        if not self.on_ground:
            self.vy += 0.5

        self.on_ground = False

        # Colisão com chão
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0.0
            self.on_ground = True

        # Colisão com plataformas
        for plat in platforms:
            if self.rect.colliderect(plat) and self.vy >= 0 and self.rect.bottom - plat.top < 20:
                self.rect.bottom = plat.top
                self.vy = 0.0
                self.on_ground = True

        # Limites do mundo
        if self.rect.x < WORLD_LEFT:
            self.rect.x = WORLD_LEFT
        if self.rect.x > WORLD_RIGHT - self.rect.width:
            self.rect.x = WORLD_RIGHT - self.rect.width

    def jump_action(self):
        if self.on_ground:
            self.vy = self.jump
            self.on_ground = False

    def draw(self, surface, cam):
        draw_rect = self.rect.move(-int(cam.x), -int(cam.y))
        pygame.draw.rect(surface, self.color, draw_rect)


# ----- Inicia estruturas de dados
game = True
clock = pygame.time.Clock()
player = Player(100, 670)
cam = Camera(WIDTH, HEIGHT, lerp=0.12, deadzone_w=380, deadzone_h=180, lookahead_x=140)

GROUND_HEIGHT = 100
GROUND_Y = WORLD_BOTTOM - GROUND_HEIGHT
ground_color = (40, 120, 40)

platform_img = pygame.image.load("assets/blocks.png").convert_alpha()
platform_img = pygame.transform.scale(platform_img, (100, 40))
NUM_PLATFORMS = 20
platforms = []
for i in range(NUM_PLATFORMS):
    x = random.randint(WORLD_LEFT + 100, WORLD_RIGHT - 200)
    y = random.randint(300, GROUND_Y - 100)
    rect = pygame.Rect(x, y, 100, 40)
    platforms.append(rect)

# ===== Loop principal =====
while game:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.jump_action()

    keys = pygame.key.get_pressed()
    player.update(keys, platforms)
    cam.update(player.rect, player.vx, WORLD_LIMITS)

    # Fundo (céu)
    window.fill((35, 60, 110))

    # Chão verde
    ground_rect = pygame.Rect(WORLD_LEFT, GROUND_Y, WORLD_RIGHT - WORLD_LEFT, GROUND_HEIGHT)
    pygame.draw.rect(window, ground_color, ground_rect.move(-int(cam.x), -int(cam.y)))

    # Desenha plataformas
    for plat in platforms:
        window.blit(platform_img, (plat.x - int(cam.x), plat.y - int(cam.y)))

    # Desenha jogador
    player.draw(window, cam)

    # HUD
    font = pygame.font.get_default_font()
    f = pygame.font.Font(font, 18)
    txt = f.render(f"Player x={int(player.rect.x)}  cam.x={int(cam.x)}", True, (255,255,255))
    window.blit(txt, (10, 10))

    pygame.display.update()
    clock.tick(60)

pygame.quit()