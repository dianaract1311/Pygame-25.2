import pygame
import random

pygame.init()

# ===== Configurações da tela =====
WIDTH, HEIGHT = 1280, 720
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Jardim Esquecido")

image = pygame.image.load("assets/background.jpg").convert()
background = pygame.transform.scale(image, (WIDTH, HEIGHT))

# ===== Chão =====
GROUND_HEIGHT = 100
GROUND_Y = HEIGHT - GROUND_HEIGHT
ground_color = (10, 9, 9)

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
        self.facing = 1
        self.lives = 3

    def update(self, keys, platforms):
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
            self.facing = -1
        if keys[pygame.K_RIGHT]:
            self.vx = self.speed
            self.facing = 1
        self.rect.x += self.vx

        self.vy += 0.7
        if self.vy > 20:
            self.vy = 20
        self.rect.y += self.vy
        self.on_ground = False

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

# ===== Inimigos fase 1 =====
class Enemy:
    def __init__(self, platform, speed=2):
        self.platform = platform
        self.width = 40
        self.height = 40
        self.left_limit = platform.left + 4
        self.right_limit = platform.right - self.width - 4
        start_x = random.randint(self.left_limit, self.right_limit)
        self.rect = pygame.Rect(start_x, platform.top - self.height, self.width, self.height)
        self.color = (0, 0, 0)
        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.alive = True

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.x <= self.left_limit:
            self.rect.x = self.left_limit
            self.direction = 1
        elif self.rect.x >= self.right_limit:
            self.rect.x = self.right_limit
            self.direction = -1
        self.rect.bottom = self.platform.top

    def draw(self, surface, cam):
        pygame.draw.rect(surface, self.color, self.rect.move(-int(cam.x), -int(cam.y)))

# ===== Inimigos fase 2 =====
class EnemyPhase2:
    def __init__(self, platform, speed=2):
        self.platform = platform
        self.width = 60
        self.height = 60
        self.left_limit = platform.left + 4
        self.right_limit = platform.right - self.width - 4
        start_x = random.randint(self.left_limit, self.right_limit)
        self.rect = pygame.Rect(start_x, platform.top - self.height, self.width, self.height)
        self.color = (0, 0, 0)
        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.alive = True
        self.hp = 2

    def update(self):
        self.rect.x += self.speed * self.direction
        if self.rect.x <= self.left_limit:
            self.rect.x = self.left_limit
            self.direction = 1
        elif self.rect.x >= self.right_limit:
            self.rect.x = self.right_limit
            self.direction = -1
        self.rect.bottom = self.platform.top

    def take_damage(self):
        self.hp -= 1
        if self.hp <= 0:
            self.alive = False

    def draw(self, surface, cam):
        pygame.draw.rect(surface, self.color, self.rect.move(-int(cam.x), -int(cam.y)))

# ===== Plataformas =====
platform_img = pygame.image.load("assets/blocks.png").convert_alpha()

NUM_PLATFORMS = 20
MIN_X_GAP = 160
MAX_X_GAP = 400
MIN_Y = GROUND_Y - 440
MAX_Y = GROUND_Y - 200
MIN_Y_DIFF = 170
MAX_Y_DIFF = 190

platforms = []
x_pos = -600
y_base = random.randint(MIN_Y, MAX_Y)

# Plataformas principais
for i in range(NUM_PLATFORMS):
    width = random.randint(280, 450)
    height = 60
    x_pos += random.randint(MIN_X_GAP, MAX_X_GAP)
    while True:
        y_variation = random.randint(-MAX_Y_DIFF, MAX_Y_DIFF)
        new_y = y_base + y_variation
        if MIN_Y <= new_y <= MAX_Y and abs(new_y - y_base) >= MIN_Y_DIFF:
            y_base = new_y
            break
    rect = pygame.Rect(x_pos, y_base, width, height)
    platforms.append(rect)

# Plataformas de recuperação
lower_platforms = []
for i in range(random.randint(4, 6)):
    width = random.randint(80, 160)
    height = 50
    x = random.randint(-400, 20000)
    y = random.randint(GROUND_Y - 120, GROUND_Y - 60)
    lower_platforms.append(pygame.Rect(x, y, width, height))

all_platforms = platforms + lower_platforms

# ===== Círculos aleatórios sobre plataformas =====
circles_on_platforms = []
for plat in platforms:  # apenas nas plataformas principais
    if random.random() < 0.3:  # 30% de chance
        cx = plat.centerx
        cy = plat.top - 15
        circles_on_platforms.append((cx, cy))

# ===== Gera inimigos fase 1 =====
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
green_circles = []

fase2_started = False
fase2_timer = 0

game_over = False

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
                    player.rect.x -= 150
                    player.rect.y -= 50
                    player.vy = 0

        for enemy in enemies:
            if enemy.alive:
                enemy.update()

        for bullet in bullets:
            bullet.update()
            for enemy in enemies:
                if enemy.alive and bullet.rect.colliderect(enemy.rect):
                    if isinstance(enemy, EnemyPhase2):
                        enemy.take_damage()
                        if not enemy.alive:
                            green_circles.append((enemy.rect.centerx, enemy.rect.centery))
                        bullet.alive = False
                    else:
                        green_circles.append((enemy.rect.centerx, enemy.rect.centery))
                        enemy.alive = False
                        bullet.alive = False

        bullets = [b for b in bullets if b.alive]
        enemies = [e for e in enemies if e.alive]

        # ===== Fase 2 =====
        if not fase2_started and player.rect.x >= 5530:
            fase2_started = True
            fase2_timer = pygame.time.get_ticks()

            enemies.clear()
            platforms.clear()
            all_platforms.clear()
            green_circles.clear()
            circles_on_platforms.clear()

            x_pos = 12000
            y_base = random.randint(MIN_Y, MAX_Y)
            for i in range(NUM_PLATFORMS):
                width = random.randint(295, 600)
                height = 60
                x_pos += random.randint(MIN_X_GAP, MAX_X_GAP)
                while True:
                    y_variation = random.randint(-MAX_Y_DIFF, MAX_Y_DIFF)
                    new_y = y_base + y_variation
                    if MIN_Y <= new_y <= MAX_Y and abs(new_y - y_base) >= MIN_Y_DIFF:
                        y_base = new_y
                        break
                rect = pygame.Rect(x_pos, y_base, width, height)
                platforms.append(rect)
            all_platforms = platforms.copy()

            for plat in random.sample(platforms, k=min(len(platforms), 20)):
                enemies.append(EnemyPhase2(plat, speed=random.randint(2, 4)))

            # círculos fase 2
            for plat in platforms:
                if random.random() < 0.3:
                    cx = plat.centerx
                    cy = plat.top - 15
                    circles_on_platforms.append((cx, cy))

    # ===== Desenho =====
    window.fill((35, 60, 110))
    window.blit(background, (0, 0))
    pygame.draw.rect(window, ground_color, (0 - int(cam.x), GROUND_Y - int(cam.y), 20000, GROUND_HEIGHT))

    # Plataformas
    for plat in all_platforms:
        pygame.draw.rect(
            window,
            ground_color,
            (plat.x - int(cam.x), plat.y - int(cam.y), plat.width, plat.height),
            border_radius=12
        )

    # Círculos sobre plataformas
    for cx, cy in circles_on_platforms:
        pygame.draw.circle(window, (0, 200, 255), (cx - int(cam.x), cy - int(cam.y)), 15)

    # Círculos verdes (inimigos mortos)
    for gx, gy in green_circles:
        pygame.draw.circle(window, (0, 255, 0), (gx - int(cam.x), gy - int(cam.y)), 15)

    # Inimigos
    for enemy in enemies:
        enemy.draw(window, cam)

    # Tiros
    for bullet in bullets:
        bullet.draw(window, cam)

    # Jogador
    player.draw(window, cam)

    # HUD
    txt = font.render(f"x={int(player.rect.x)}  Lives={player.lives}", True, (255,255,255))
    window.blit(txt, (10, 10))

    # Fase 2
    if fase2_started:
        elapsed = pygame.time.get_ticks() - fase2_timer
        if elapsed < 2000:
            fase2_txt = font.render("FASE 2", True, (255, 255, 0))
            window.blit(fase2_txt, (WIDTH//2 - 50, HEIGHT//2 - 20))

    pygame.display.update()
    clock.tick(40)

pygame.quit()