import pygame
import random
import math
import os #facilitar o uso das imagens/sprites

pygame.init()

# ===== Configurações da tela =====
WIDTH, HEIGHT = 1280, 720
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jardim Esquecido")

# Carrega o background uma vez
image = pygame.image.load("assets/background.jpg").convert()
background = pygame.transform.scale(image, (WIDTH, HEIGHT))

# ===== Chão =====
GROUND_HEIGHT = 100
GROUND_Y = HEIGHT - GROUND_HEIGHT
ground_color = (10, 9, 9)

# ===== Limites do mapa (duas telas em sequência) =====
MAP_WIDTH = WIDTH * 2  # duas telas lado a lado
MAP_HEIGHT = HEIGHT
WALL_WIDTH = 40  # largura das paredes laterais

# ===== carrega sprite strip e divide em frames =====
def load_strip(path, frames_count):
    """Carrega uma imagem tipo sprite strip horizontal e retorna lista de frames Surface."""
    img = pygame.image.load(path).convert_alpha()
    w, h = img.get_size()
    frame_w = w // frames_count
    frames = []
    for i in range(frames_count):
        rect = pygame.Rect(i * frame_w, 0, frame_w, h)
        frame = pygame.Surface((frame_w, h), pygame.SRCALPHA)
        frame.blit(img, (0, 0), rect)
        frames.append(frame)
    return frames

# ===== Câmera =====
class Camera:
    def _init_(self, w, h, lerp=0.12, lookahead_x=140):
        self.w, self.h = w, h
        self.lerp = lerp
        self.lookahead_x = lookahead_x
        self.x, self.y = 0.0, 0.0
        self._current_look_x = 0.0
        self._look_smooth = 0.12

    def _lerp(self, a, b, t):
        return a + (b - a) * t

    def update(self, player_rect, player_vx):
        target_x = player_rect.centerx - self.w / 2
        target_y = player_rect.centery - self.h / 2
        look_target = (1 if player_vx > 0 else -1 if player_vx < 0 else 0) * self.lookahead_x
        self._current_look_x = self._lerp(self._current_look_x, look_target, self._look_smooth)
        target_x += self._current_look_x
        self.x = self._lerp(self.x, target_x, self.lerp)
        self.y = self._lerp(self.y, target_y, self.lerp)

        # Clamp da câmera para não sair dos limites do mapa
        if self.x < 0:
            self.x = 0
        if self.x > MAP_WIDTH - self.w:
            self.x = MAP_WIDTH - self.w
        if self.y < 0:
            self.y = 0
        if self.y > MAP_HEIGHT - self.h:
            self.y = MAP_HEIGHT - self.h

# ===== Jogador (com invulnerabilidade) =====
class Player:
    def _init_(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.color = (255, 0, 0)
        self.vx = 0
        self.vy = 0
        self.speed = 5
        self.jump = -18
        self.on_ground = False
        self.facing = 1
        self.lives = 4  # 4 vidas conforme pedido

        # Invulnerabilidade após tomar dano
        self.invulnerable = False
        self.invuln_start = 0            # pygame.time.get_ticks() quando a invuln começou
        self.invuln_duration = 2000      # duração em ms (2 segundos)
        self.blink_interval = 150        # ms para piscar enquanto invulnerável

    def update(self, keys, platforms, walls):
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
            self.facing = -1
        if keys[pygame.K_RIGHT]:
            self.vx = self.speed
            self.facing = 1
        self.rect.x += self.vx

        # Checagem de colisão simples com paredes laterais (impede atravessar)
        for wall in walls:
            if self.rect.colliderect(wall):
                if self.vx > 0:  # movendo para a direita, colidiu na parede direita
                    self.rect.right = wall.left
                elif self.vx < 0:  # movendo para a esquerda
                    self.rect.left = wall.right
                       
        # Gravidade
        self.vy += 0.7
        if self.vy > 20:
            self.vy = 20
        self.rect.y += self.vy
        self.on_ground = False

        # Colisão com plataformas (simples, por eixo Y)
        for plat in platforms:
            if self.vy > 0 and self.rect.colliderect(plat):
                overlap_x = min(self.rect.right, plat.right) - max(self.rect.left, plat.left)
                if overlap_x > 25 and self.rect.bottom <= plat.top + 20:
                    self.rect.bottom = plat.top
                    self.vy = 0
                    self.on_ground = True

        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True

        # ===== Limites do mapa =====
        MAP_LEFT_LIMIT = 0
        MAP_RIGHT_LIMIT = 6000

        if self.rect.left < MAP_LEFT_LIMIT:
            self.rect.left = MAP_LEFT_LIMIT
        if self.rect.right > MAP_RIGHT_LIMIT:
            self.rect.right = MAP_RIGHT_LIMIT

    def jump_action(self):
        if self.on_ground:
            self.vy = self.jump
            self.on_ground = False

    def draw(self, surface, cam):
        pygame.draw.rect(surface, self.color, self.rect.move(-int(cam.x), -int(cam.y)))

# ===== Classe do tiro =====
class Bullet:
    def __init__(self, x, y, direction):
        self.rect = pygame.Rect(x, y, 10, 10)
        self.color = (255, 255, 0)
        self.speed = 12 * direction
        self.alive = True

    def update(self):
        self.rect.x += self.speed
        if self.rect.x < -5000 or self.rect.x > 20000:
            self.alive = False

    def draw(self, surface, cam):
        pygame.draw.circle(surface, self.color, (self.rect.centerx - int(cam.x), self.rect.centery - int(cam.y)), 5)

# ===== Inimigos animados =====
class Enemy:
    def __init__(self, platform, speed=2):
        self.platform = platform
        self.width = 60
        self.height = 60
        self.left_limit = platform.left + 4
        self.right_limit = platform.right - self.width - 4
        start_x = random.randint(self.left_limit, self.right_limit)
        self.rect = pygame.Rect(start_x, platform.top - self.height - 5, self.width, self.height)
        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.alive = True
        self.frames = [
            pygame.transform.scale(pygame.image.load("assets/fly1.png").convert_alpha(), (self.width, self.height)),
            pygame.transform.scale(pygame.image.load("assets/fly2.png").convert_alpha(), (self.width, self.height))
        ]
        self.frame_index = 0
        self.animation_speed = 0.2
        self.animation_timer = 0

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.x <= self.left_limit:
            self.rect.x = self.left_limit
            self.direction = 1
        elif self.rect.x >= self.right_limit:
            self.rect.x = self.right_limit
            self.direction = -1
        self.rect.bottom = self.platform.top - 5
        self.animation_timer += self.animation_speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.frames)

    def draw(self, surface, cam):
        frame = self.frames[self.frame_index]
        if self.direction == 1:
            frame = pygame.transform.flip(frame, True, False)
        surface.blit(frame, (self.rect.x - int(cam.x), self.rect.y - int(cam.y)))

# ===== Plataformas =====
NUM_PLATFORMS = 15
MIN_X_GAP = 190
MAX_X_GAP = 400
MIN_Y = GROUND_Y - 440
MAX_Y = GROUND_Y - 200
MIN_Y_DIFF = 170
MAX_Y_DIFF = 250

platforms = []
x_pos = -600
y_base = random.randint(MIN_Y, MAX_Y)

for i in range(NUM_PLATFORMS):
    width = random.randint(280, 450)
    height = 60
    x_pos += random.randint(MIN_X_GAP, MAX_X_GAP)
    # ===== Substituindo while True por loop seguro =====
    for _ in range(100):
        y_variation = random.randint(-MAX_Y_DIFF, MAX_Y_DIFF)
        new_y = y_base + y_variation
        if MIN_Y <= new_y <= MAX_Y and abs(new_y - y_base) >= MIN_Y_DIFF:
            y_base = new_y
            break
    else:
        y_base = max(MIN_Y, min(MAX_Y, y_base + random.randint(-MAX_Y_DIFF, MAX_Y_DIFF)))
    rect = pygame.Rect(x_pos, y_base, width, height)
    platforms.append(rect)

# ===== Plataforma inicial de recuperação =====
lower_platforms = []
initial_platform_width = 160
initial_platform_height = 50
initial_platform_x = 100
initial_platform_y = GROUND_Y - 120
lower_platforms.append(pygame.Rect(initial_platform_x, initial_platform_y, initial_platform_width, initial_platform_height))

all_platforms = platforms + lower_platforms

# ===== Gera inimigos =====
enemies = []
for plat in random.sample(platforms, k=min(len(platforms), 20)):
    enemies.append(Enemy(plat, speed=random.randint(2, 4)))

ground_platform = pygame.Rect(0, GROUND_Y, 20000, 60)
for i in range(6):
    enemies.append(Enemy(ground_platform, speed=random.randint(2, 3)))

# ===== Setup inicial =====
clock = pygame.time.Clock()
player = Player(100, GROUND_Y - 50)
cam = Camera(WIDTH, HEIGHT)
font = pygame.font.Font(pygame.font.get_default_font(), 24)
bullets = []
orbes = []

game_over = False
start_time = pygame.time.get_ticks()
enemies_defeated = 0

# ===== Loop principal =====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if not game_over and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.jump_action()
            if event.key == pygame.K_e:
                bx = player.rect.centerx + (player.facing * 30)
                by = player.rect.centery
                bullets.append(Bullet(bx, by, player.facing))

    keys = pygame.key.get_pressed()

    if not game_over:
        player.update(keys, all_platforms)
        cam.update(player.rect, player.vx)

        for enemy in enemies:
            if enemy.alive and player.rect.colliderect(enemy.rect):
                player.lives -= 1
                if player.lives <= 0:
                    game_over = True
                else:
                    # Teleporta jogador para trás, mas evita sair do mapa
                    player.rect.x = max(0, player.rect.x - 150)
                    player.rect.y = max(0, player.rect.y - 50)
                    player.vy = 0

        for enemy in enemies:
            if enemy.alive:
                enemy.update()

        for bullet in bullets:
            bullet.update()
            # Limite de colisões por frame para performance
            for enemy in enemies:
                if enemy.alive and bullet.rect.colliderect(enemy.rect):
                    orbes.append(pygame.Rect(enemy.rect.centerx - 10, enemy.rect.centery - 10, 20, 20))
                    enemy.alive = False
                    bullet.alive = False
                    enemies_defeated += 1
                    break  # evita múltiplas colisões do mesmo tiro

        bullets = [b for b in bullets if b.alive]
        enemies = [e for e in enemies if e.alive]

        # Coleta de orbes
        for orb in orbes[:]:
            if player.rect.colliderect(orb):
                player.orbes_collected += 1
                orbes.remove(orb)

        # ===== Verifica tempo de jogo =====
        elapsed_seconds = (pygame.time.get_ticks() - start_time) // 1000
        if elapsed_seconds >= 45:
            game_over = True
            if player.orbes_collected >= 15:
                phase_result = "FASE 2 DESBLOQUEADA!"
            else:
                phase_result = "GAME OVER - poucos inimigos derrotados."

    # ===== Desenho =====
    window.fill((35, 60, 110))
    window.blit(background, (0, 0))
    pygame.draw.rect(window, ground_color, (0 - int(cam.x), GROUND_Y - int(cam.y), 6000, GROUND_HEIGHT))

    for plat in all_platforms:
        pygame.draw.rect(
            window,
            ground_color,
            (plat.x - int(cam.x), plat.y - int(cam.y), plat.width, plat.height),
            border_radius=12
        )

    for orb in orbes:
        pygame.draw.circle(window, (0, 255, 0), (orb.centerx - int(cam.x), orb.centery - int(cam.y)), 10)

    for enemy in enemies:
        enemy.draw(window, cam)

    for bullet in bullets:
        bullet.draw(window, cam)

    player.draw(window, cam)

    txt = font.render(f"x={int(player.rect.x)}  Lives={player.lives}  Time={elapsed_seconds}s  Orbes={player.orbes_collected}", True, (255,255,255))
    window.blit(txt, (10, 10))

    if game_over:
        if 'phase_result' in locals():
            msg = phase_result
        else:
            msg = "GAME OVER"
        msg_surface = font.render(msg, True, (255, 255, 0))
        window.blit(msg_surface, (WIDTH // 2 - msg_surface.get_width() // 2, HEIGHT // 2 - 20))
        pygame.display.update()
        pygame.time.wait(4000)
        running = False

    pygame.display.update()
    clock.tick(40)

pygame.quit()