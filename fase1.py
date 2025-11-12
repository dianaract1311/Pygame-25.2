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

        # Limites do mapa (colisão final com paredes)
        MAP_LEFT_LIMIT = WALL_WIDTH
        MAP_RIGHT_LIMIT = MAP_WIDTH - WALL_WIDTH

        if self.rect.left < MAP_LEFT_LIMIT:
            self.rect.left = MAP_LEFT_LIMIT
        if self.rect.right > MAP_RIGHT_LIMIT:
            self.rect.right = MAP_RIGHT_LIMIT

        # Atualiza estado de invulnerabilidade
        if self.invulnerable:
            elapsed = pygame.time.get_ticks() - self.invuln_start
            if elapsed >= self.invuln_duration:
                self.invulnerable = False

    def jump_action(self):
        if self.on_ground:
            self.vy = self.jump
            self.on_ground = False

    def take_damage(self):
        """Aplica dano: decrementa vida e inicia invulnerabilidade (se já invulnerável, ignora)."""
        if self.invulnerable:
            return False  # não sofreu dano pois já invulnerável
        self.lives -= 1
        self.invulnerable = True
        self.invuln_start = pygame.time.get_ticks()
        return True

    def draw(self, surface, cam):
        # Se estiver invulnerável, faz blink (pisca) para indicar
        if self.invulnerable:
            elapsed = pygame.time.get_ticks() - self.invuln_start
            visible = (elapsed // self.blink_interval) % 2 == 0
            if visible:
                pygame.draw.rect(surface, self.color, self.rect.move(-int(cam.x), -int(cam.y)))
        else:
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
        # destruir se sair fora do mapa
        if self.rect.right < 0 or self.rect.left > MAP_WIDTH:
            self.alive = False

    def draw(self, surface, cam):
        pygame.draw.circle(surface, self.color, (self.rect.centerx - int(cam.x), self.rect.centery - int(cam.y)), 5)

        # ===== Inimigos: agora apenas a animação de WALK usando o strip indicado =====
class Enemy:
    def _init_(self, platform, speed=2, sprite_size=(45,45)):
        self.platform = platform
        self.width, self.height = sprite_size

        self.left_limit = platform.left + 4
        self.right_limit = platform.right - self.width - 4
        start_x = random.randint(max(self.left_limit, WALL_WIDTH + 4), min(self.right_limit, MAP_WIDTH - WALL_WIDTH - 4))
        self.rect = pygame.Rect(start_x, platform.top - self.height, self.width, self.height)

        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.alive = True
        self.dying = False
        self.dead_finished = False

        # Carrega apenas a strip de walk que você informou estar em:
        # assets/slime/slime_walk_anim_strip_15.png
        walk_path = os.path.join("assets", "slime", "slime_walk_anim_strip_15.png")
        try:
            walk_frames = load_strip(walk_path, 15)
            # normaliza tamanho
            norm_walk = []
            for f in walk_frames:
                if f.get_size() != (self.width, self.height):
                    norm_walk.append(pygame.transform.smoothscale(f, (self.width, self.height)))
                else:
                    norm_walk.append(f)
            self.walk_right = norm_walk
            self.walk_left = [pygame.transform.flip(f, True, False) for f in self.walk_right]
        except Exception as e:
            print(f"Erro carregando {walk_path}: {e}")
            # fallback: superfície simples
            fallback = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            fallback.fill((0,180,0))
            self.walk_right = [fallback]
            self.walk_left = [pygame.transform.flip(fallback, True, False)]

        # usa walk frames também como idle (simples)
        self.idle_right = [self.walk_right[0]]
        self.idle_left = [self.walk_left[0]]

        # estado/frames
        self.state = "walk"
        self.frame_index = 0
        self.animation_speed = 0.18
        self.animation_timer = 0

    def update(self):
        if self.dead_finished:
            return
        # Movimento
        if not self.dying:
            self.rect.x += self.speed * self.direction
            if self.rect.x <= self.left_limit:
                self.rect.x = self.left_limit
                self.direction = 1
            elif self.rect.x >= self.right_limit:
                self.rect.x = self.right_limit
                self.direction = -1
            self.rect.bottom = self.platform.top - 5

            # definir estado
            self.state = "walk"
        else:
            self.rect.bottom = self.platform.top - 5

        # animação
        self.animation_timer += self.animation_speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            self.frame_index += 1
            if self.state == "walk":
                frames = self.walk_right if self.direction == 1 else self.walk_left
                if self.frame_index >= len(frames):
                    self.frame_index = 0
            else:
                self.frame_index = 0

    def start_death(self):
        # aqui apenas marca como não-alive; não temos animação de death por enquanto
        self.alive = False
        self.dead_finished = True

    def draw(self, surface, cam):
        if self.dead_finished:
            return
        if self.state == "walk":
            frames = self.walk_right if self.direction == 1 else self.walk_left
        else:
            frames = self.idle_right if self.direction == 1 else self.idle_left
        idx = self.frame_index % len(frames)
        frame = frames[idx]
        surface.blit(frame, (self.rect.x - int(cam.x), self.rect.y - int(cam.y)))

        
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

# ===== Plataformas FIXAS (layout "coringa") =====
PLATFORMS_FIXED = [
    # Tela 1 (0 .. WIDTH)
    (WALL_WIDTH + 120, GROUND_Y - 180, 360, 40),
    (WALL_WIDTH + 520, GROUND_Y - 300, 280, 40),
    (WALL_WIDTH + 880, GROUND_Y - 220, 320, 40),
    (WALL_WIDTH + 300, GROUND_Y - 420, 220, 40),
    # Tela 2 (WIDTH .. MAP_WIDTH)
    (WIDTH + 100, GROUND_Y - 160, 400, 40),
    (WIDTH + 540, GROUND_Y - 260, 260, 40),
    (WIDTH + 920, GROUND_Y - 340, 300, 40),
    (WIDTH + 720, GROUND_Y - 120, 220, 40),
]

platforms = [pygame.Rect(x, y, w, h) for (x, y, w, h) in PLATFORMS_FIXED]

# Plataformas baixas (recuperação) fixas
lower_platforms = [
    pygame.Rect(WALL_WIDTH + 60, GROUND_Y - 90, 120, 40),
    pygame.Rect(WIDTH + 220, GROUND_Y - 90, 140, 40),
    pygame.Rect(WALL_WIDTH + 820, GROUND_Y - 90, 160, 40),
]

all_platforms = platforms + lower_platforms

# ===== Orbes (coletáveis) colocadas em plataformas fixas =====
orbs = []
orb_radius = 10
orb_platform_indices = [0, 2, 4, 6]  # índices de PLATFORMS_FIXED onde haverá orbe
for idx in orb_platform_indices:
    if idx < len(platforms):
        plat = platforms[idx]
        ox = plat.centerx
        oy = plat.top - 15
        orbs.append(pygame.Rect(ox - orb_radius, oy - orb_radius, orb_radius * 2, orb_radius * 2))

total_orbs = len(orbs)
collected_orbs = 0

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