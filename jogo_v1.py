import pygame
import random

pygame.init()

# ===== Configurações da tela =====
WIDTH, HEIGHT = 1280, 720
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jardim Esquecido")

# ===== Chão =====
GROUND_HEIGHT = 100
GROUND_Y = HEIGHT - GROUND_HEIGHT
ground_color = (40, 120, 40)

# ===== Câmera =====
class Camera:
    def __init__(self, w, h, lerp=0.12, lookahead_x=140):
        self.w, self.h = w, h
        self.lerp = lerp
        self.lookahead_x = lookahead_x
        self.x, self.y = 0.0, 0.0
        self._current_look_x = 0.0
        self._look_smooth = 0.12

    def _lerp(self, a, b, t): return a + (b - a) * t

    def update(self, player_rect, player_vx):
        target_x = player_rect.centerx - self.w / 2
        target_y = player_rect.centery - self.h / 2
        look_target = (1 if player_vx > 0 else -1 if player_vx < 0 else 0) * self.lookahead_x
        self._current_look_x = self._lerp(self._current_look_x, look_target, self._look_smooth)
        target_x += self._current_look_x
        self.x = self._lerp(self.x, target_x, self.lerp)
        self.y = self._lerp(self.y, target_y, self.lerp)

# ===== Jogador =====
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.color = (255, 0, 0)
        self.vx = 0
        self.vy = 0
        self.speed = 5
        self.jump = -18
        self.on_ground = False

    def update(self, keys, platforms):
        # Movimento horizontal
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
        if keys[pygame.K_RIGHT]:
            self.vx = self.speed
        self.rect.x += self.vx

        # Gravidade
        self.vy += 0.7
        if self.vy > 20:
            self.vy = 20
        self.rect.y += self.vy
        self.on_ground = False

        # Colisões verticais com plataformas
        for plat in platforms:
            if self.vy > 0 and self.rect.colliderect(plat):
                overlap_x = min(self.rect.right, plat.right) - max(self.rect.left, plat.left)
                if overlap_x > 25 and self.rect.bottom <= plat.top + 20:
                    self.rect.bottom = plat.top
                    self.vy = 0
                    self.on_ground = True

        # Chão
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True

    def jump_action(self):
        if self.on_ground:
            self.vy = self.jump
            self.on_ground = False

    def draw(self, surface, cam):
        pygame.draw.rect(surface, self.color, self.rect.move(-int(cam.x), -int(cam.y)))

# ===== Plataformas =====
platform_img = pygame.image.load("assets/blocks.png").convert_alpha()

NUM_PLATFORMS = 40  # mais plataformas
MIN_X_GAP = 170     # distância mínima entre plataformas
MAX_X_GAP = 400     # distância máxima entre plataformas
MIN_Y = GROUND_Y - 320
MAX_Y = GROUND_Y - 200
MIN_Y_DIFF = 50     # diferença mínima de altura entre plataformas
MAX_Y_DIFF = 180    # diferença máxima de altura entre plataformas

platforms = []
x_pos = -600  # começa um pouco antes do jogador
y_base = random.randint(MIN_Y, MAX_Y)

for i in range(NUM_PLATFORMS):
    width = random.randint(120, 280)
    height = 60
    x_pos += random.randint(MIN_X_GAP, MAX_X_GAP)

    # gerar altura da próxima plataforma com diferença mínima e máxima
    while True:
        y_variation = random.randint(-MAX_Y_DIFF, MAX_Y_DIFF)
        new_y = y_base + y_variation
        if MIN_Y <= new_y <= MAX_Y and abs(new_y - y_base) >= MIN_Y_DIFF:
            y_base = new_y
            break

    rect = pygame.Rect(x_pos, y_base, width, height)
    platforms.append(rect)

# ===== Setup inicial =====
clock = pygame.time.Clock()
player = Player(100, GROUND_Y - 50)
cam = Camera(WIDTH, HEIGHT)

# ===== Loop principal =====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            player.jump_action()

    keys = pygame.key.get_pressed()
    player.update(keys, platforms)
    cam.update(player.rect, player.vx)

    # Fundo
    window.fill((35, 60, 110))

    # Chão
    pygame.draw.rect(window, ground_color, (0 - int(cam.x), GROUND_Y - int(cam.y), 20000, GROUND_HEIGHT))

    # Plataformas
    for plat in platforms:
        scaled = pygame.transform.scale(platform_img, (plat.width, plat.height))
        window.blit(scaled, (plat.x - int(cam.x), plat.y - int(cam.y)))

    # Jogador
    player.draw(window, cam)

    # HUD
    font = pygame.font.Font(pygame.font.get_default_font(), 18)
    txt = font.render(f"x={int(player.rect.x)}", True, (255,255,255))
    window.blit(txt, (10, 10))

    pygame.display.update()
    clock.tick(60)

pygame.quit()