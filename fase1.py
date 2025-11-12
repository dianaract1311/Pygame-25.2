import pygame
import random
import math 
import os #facilitar o uso das imagens/sprites
import json #permite leitura de arquivos JSON, para armazenar dados do ranking (dica do ChatGPT)

pygame.init()

# inicializa o mixer de áudio
pygame.mixer.init()

# Carrega o som do tiro
tiro = pygame.mixer.Sound("assets/snd/gunfire_sfx.wav")
jump = pygame.mixer.Sound("assets/snd/SFX_Jump_03.wav")
# --- Adicionado: som de dano (golpe) ---
try:
    golpe = pygame.mixer.Sound(os.path.join("assets", "snd", "golpe.mp3"))
except Exception as e:
    print(f"Aviso: não foi possível carregar golpe.mp3: {e}")
    golpe = None

# inicia o timer somente quando o jogo começa
start_time = pygame.time.get_ticks()
time_elapsed_ms = 0

# toca música de fundo em loop (-1 = loop infinito) -- ChatGPT
music_path = os.path.join("assets", "snd", "musica_fundo.mp3")
try:
    pygame.mixer.music.load(music_path)
    pygame.mixer.music.set_volume(0.6)  # ajuste entre 0.0 e 1.0 conforme quiser
    pygame.mixer.music.play(-1)  # -1 = toca em loop infinito
except Exception as e:
    print(f"Aviso: não foi possível tocar a música: {e}")

# ===== Configurações da tela =====
WIDTH, HEIGHT = 1280, 720 # resolução da tela
window = pygame.display.set_mode((WIDTH, HEIGHT)) # aplica a resolução na tela
pygame.display.set_caption("Forest Jump") # nome do jogo

# Carrega o background uma vez
image = pygame.image.load("assets/background.jpg").convert()
background = pygame.transform.scale(image, (WIDTH, HEIGHT))

# ===== Chão =====
GROUND_HEIGHT = 100 # 100px para cima
GROUND_Y = HEIGHT - GROUND_HEIGHT #calcula a coordenada Y do topo do chão com base na altura da janela e na altura do chão
ground_color = (10, 9, 9)

# ===== Limites do mapa (duas telas em sequência) =====
MAP_WIDTH = WIDTH * 2  # duas telas lado a lado
MAP_HEIGHT = HEIGHT
WALL_WIDTH = 40  # largura das paredes laterais

# ===== carrega sprite strip e divide em frames =====
def load_strip(path, frames_count):
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
    def __init__(self, w, h, lerp=0.12, lookahead_x=140):
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

from PIL import Image # importa biblioteca Pillow para ler os sprites de gif

def load_gif_frames(path):
    frames = []
    pil_image = Image.open(path)
    try:
        while True:
            # Converte frame atual para RGBA (transparente)
            frame = pil_image.convert("RGBA")
            # Converte para Surface compatível com pygame
            pygame_image = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frames.append(pygame_image.copy())
            pil_image.seek(pil_image.tell() + 1)
    except EOFError:
        pass  # acabou o GIF

    return frames

# ===== Jogador (com invulnerabilidade) =====
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
        self.lives = 4  # 4 vidas conforme pedido

        # Invulnerabilidade após tomar dano
        self.invulnerable = False
        self.invuln_start = 0            # pygame.time.get_ticks() quando a invuln começou
        self.invuln_duration = 2000      # duração em ms (2 segundos)
        self.blink_interval = 150        # ms para piscar enquanto invulnerável

        # ===== Carrega frames de corrida (run.gif) =====
        run_path = os.path.join("assets", "run.gif")
        frames = []
        try:
            frames = load_gif_frames(run_path)
        except Exception as e:
            print(f"Erro carregando run.gif: {e}")
            frames = []
        
        # ===== Carrega frames de idle (idle.gif) =====
        idle_path = os.path.join("assets", "idle.gif")
        self.idle_frames_right = []
        self.idle_frames_left = []
        try:
            idle_frames = load_gif_frames(idle_path)
            self.idle_frames_right = [
                pygame.transform.smoothscale(f, (self.rect.width, self.rect.height))
                for f in idle_frames
            ]
            self.idle_frames_left = [pygame.transform.flip(f, True, False) for f in self.idle_frames_right]
        except Exception as e:
            print(f"Aviso: não foi possível carregar idle.gif: {e}")
            # fallback — será preenchido mais abaixo se necessário

        # Redimensiona frames para o tamanho do jogador
        self.run_frames_right = [
            pygame.transform.smoothscale(f, (self.rect.width, self.rect.height))
            for f in frames
        ]
        # Cria frames invertidos (para andar à esquerda)
        self.run_frames_left = [pygame.transform.flip(f, True, False) for f in self.run_frames_right]
        self.frame_index = 0
        self.animation_speed = 0.2
        self.animation_timer = 0

        # Se idle não foi carregado, usa um fallback a partir de run
        if len(self.idle_frames_right) == 0 and len(self.run_frames_right) > 0:
            self.idle_frames_right = [self.run_frames_right[0]]
            self.idle_frames_left = [self.run_frames_left[0]]

        # ===== Carrega sprite de pulo (jump.png) =====
        jump_path = os.path.join("assets", "jump.png")
        self.jump_frame = None
        try:
            jimg = pygame.image.load(jump_path).convert_alpha()
            # **Alteração**: redimensionar o frame de pulo para exatamente o mesmo tamanho do rect
            self.jump_frame = pygame.transform.smoothscale(jimg, (self.rect.width, self.rect.height))
        except Exception as e:
            # se falhar, apenas mantemos jump_frame = None (fallback será o comportamento anterior)
            print(f"Aviso: não foi possível carregar jump.png: {e}")
            self.jump_frame = None

    def update(self, keys, platforms, walls):
        self.vx = 0
        if keys[pygame.K_LEFT]:
            self.vx = -self.speed
            self.facing = -1
        if keys[pygame.K_RIGHT]:
            self.vx = self.speed
            self.facing = 1
        self.rect.x += self.vx
        if self.vx != 0:
            self.animation_timer += self.animation_speed
            if self.animation_timer >= 1:
                self.animation_timer = 0
                if len(self.run_frames_right) > 0:
                    self.frame_index = (self.frame_index + 1) % len(self.run_frames_right)
        else:
            self.frame_index = 0


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
        # Blink: quando invulnerável, alterna visibilidade; quando invisível, não desenha nada.
        if self.invulnerable:
            elapsed = pygame.time.get_ticks() - self.invuln_start
            visible = (elapsed // self.blink_interval) % 2 == 0
        else:
            visible = True

        if not visible:
            return  # não desenha nada

        # Se estiver no ar, desenha o sprite de pulo (se disponível)
        if not self.on_ground and self.jump_frame is not None:
            # desenha o sprite de pulo no mesmo tamanho e posição do rect
            frame = self.jump_frame
            surface.blit(frame, (self.rect.x - int(cam.x), self.rect.y - int(cam.y)))
            return

        # Escolhe sprite conforme estado do jogador
        if not self.on_ground and self.jump_frame is not None:
            # no ar → sprite de pulo
            frame = self.jump_frame
        elif self.vx != 0 and len(self.run_frames_right) > 0:
            # andando → animação de corrida
            frames = self.run_frames_right if self.facing == 1 else self.run_frames_left
            frame = frames[self.frame_index % len(frames)]
        elif len(self.idle_frames_right) > 0:
            # parado no chão → idle animado
            idle_frames = self.idle_frames_right if self.facing == 1 else self.idle_frames_left
            frame = idle_frames[(pygame.time.get_ticks() // 150) % len(idle_frames)]
        else:
            # fallback
            frame = self.run_frames_right[0] if len(self.run_frames_right) > 0 else pygame.Surface((self.rect.width, self.rect.height))

        surface.blit(frame, (self.rect.x - int(cam.x), self.rect.y - int(cam.y)))


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

# ===== Inimigos (slimes) =====
class Enemy:
    def __init__(self, platform, speed=2, sprite_size=(45,45)):
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
            self.rect.bottom = self.platform.top

            # definir estado
            self.state = "walk"
        else:
            self.rect.bottom = self.platform.top

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

# ===== Novos inimigos: GroundEnemy (mushroom GIF) =====
class GroundEnemy:
    def __init__(self, x_center, ground_y, speed=2, sprite_size=(45,45)):
        self.width, self.height = sprite_size
        # posiciona no chão com center x fornecido
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.centerx = x_center
        self.rect.bottom = ground_y

        # limites de patrulha no chão (mantém dentro das paredes)
        self.left_limit = WALL_WIDTH + 10
        self.right_limit = MAP_WIDTH - WALL_WIDTH - 10

        self.speed = speed
        self.direction = random.choice([-1, 1])
        self.alive = True
        self.dead_finished = False

        # Carrega frames do GIF mushroom_walk_anim.gif
        self.walk_right = []
        self.walk_left = []
        try:
            mpath = os.path.join("assets", "mushroom_walk_anim.gif")
            mframes = load_gif_frames(mpath)
            norm = []
            for f in mframes:
                if f.get_size() != (self.width, self.height):
                    norm.append(pygame.transform.smoothscale(f, (self.width, self.height)))
                else:
                    norm.append(f)
            self.walk_right = norm if len(norm) > 0 else [pygame.Surface((self.width, self.height), pygame.SRCALPHA)]
            self.walk_left = [pygame.transform.flip(f, True, False) for f in self.walk_right]
        except Exception as e:
            print(f"Erro carregando mushroom GIF: {e}")
            fallback = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            fallback.fill((120,80,0))
            self.walk_right = [fallback]
            self.walk_left = [pygame.transform.flip(fallback, True, False)]

        self.frame_index = 0
        self.animation_speed = 0.18
        self.animation_timer = 0

    def update(self):
        if self.dead_finished:
            return
        # Move horizontalmente apenas no chão entre left_limit e right_limit
        self.rect.x += self.speed * self.direction
        if self.rect.left <= self.left_limit:
            self.rect.left = self.left_limit
            self.direction = 1
        elif self.rect.right >= self.right_limit:
            self.rect.right = self.right_limit
            self.direction = -1

        self.rect.bottom = GROUND_Y  # garante que fica no chão

        # animação
        self.animation_timer += self.animation_speed
        if self.animation_timer >= 1:
            self.animation_timer = 0
            self.frame_index = (self.frame_index + 1) % len(self.walk_right)

    def start_death(self):
        self.alive = False
        self.dead_finished = True

    def draw(self, surface, cam):
        if self.dead_finished:
            return
        frames = self.walk_right if self.direction == 1 else self.walk_left
        frame = frames[self.frame_index % len(frames)]
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

# ===== Orbes (coletáveis) - agora 10 orbes =====
def create_orbs(total):
    """Cria uma lista de rects para 'total' orbes, priorizando plataformas fixas, depois espalhando no chão."""
    orbs_local = []
    orb_radius_local = 10
    # use os centros das primeiras plataformas possíveis
    candidates = []
    for p in platforms:
        candidates.append((p.centerx, p.top - 15))
    # também adicione alguns pontos no chão espalhados
    ground_candidates = []
    spacing = MAP_WIDTH // (total + 1)
    for i in range(1, total + 1):
        gx = i * spacing
        gy = GROUND_Y - 20
        ground_candidates.append((gx, gy))
    combined = candidates + ground_candidates
    # pick up to 'total' positions deterministically (para evitar colisões aleatórias)
    chosen = []
    idx = 0
    while len(chosen) < total and idx < len(combined):
        chosen.append(combined[idx])
        idx += 1
    # if still not enough (very unlikely), fill with random ground points
    while len(chosen) < total:
        rx = random.randint(WALL_WIDTH + 50, MAP_WIDTH - WALL_WIDTH - 50)
        ry = GROUND_Y - 20
        chosen.append((rx, ry))
    for (ox, oy) in chosen[:total]:
        orbs_local.append(pygame.Rect(int(ox - orb_radius_local), int(oy - orb_radius_local), orb_radius_local * 2, orb_radius_local * 2))
    return orbs_local

TOTAL_ORBS = 10
orbs = create_orbs(TOTAL_ORBS)
orb_radius = 10
total_orbs = TOTAL_ORBS
collected_orbs = 0
orb_platform_indices = []  # mantido vazio para evitar uso anterior de reconstrução por índice

# ===== Gera inimigos - sobre as plataformas principais =====
def create_enemies_on_platforms():
    lst = []
    for plat in platforms:
        enemy = Enemy(plat, speed=2, sprite_size=(45,45))
        # posiciona o inimigo exatamente no centro da plataforma
        enemy.rect.centerx = plat.centerx
        enemy.rect.bottom = plat.top
        # define direção inicial para alternar (opcional)
        enemy.direction = 1 if plat.centerx % 2 == 0 else -1
        lst.append(enemy)
    return lst

def create_ground_enemies(num):
    positions = []
    min_x = WALL_WIDTH + 50
    max_x = MAP_WIDTH - WALL_WIDTH - 50
    min_dist = 300  # distância mínima entre inimigos
    attempts = 0
    while len(positions) < num and attempts < 2000:
        attempts += 1
        x = random.randint(min_x, max_x)
        if all(abs(x - px) >= min_dist for px in positions):
            positions.append(x)
    lst = []
    for x in positions:
        ge = GroundEnemy(x, GROUND_Y, speed=2, sprite_size=(45,45))
        lst.append(ge)
    return lst

enemies = create_enemies_on_platforms() + create_ground_enemies(7)


# ===== Setup inicial =====
clock = pygame.time.Clock()
player = Player(WALL_WIDTH + 100, GROUND_Y - 50)
cam = Camera(WIDTH, HEIGHT)
font = pygame.font.Font(pygame.font.get_default_font(), 24)
timer_icon = pygame.image.load(os.path.join("assets", "timer_pygame.png")).convert_alpha()
timer_icon = pygame.transform.smoothscale(timer_icon, (28, 28))
bullets = []
green_circles = []

# Paredes laterais (retângulos sólidos)
left_wall = pygame.Rect(0, 0, WALL_WIDTH, MAP_HEIGHT)
right_wall = pygame.Rect(MAP_WIDTH - WALL_WIDTH, 0, WALL_WIDTH, MAP_HEIGHT)
walls = [left_wall, right_wall]

game_over = False
game_won = False
# start_time será definido quando o jogador apertar espaço na tela inicial/lobby
start_time = None
enemies_defeated = 0


# ===== Ranking (persistente) =====
HIGHSCORES_FILE = "highscores.json"

def load_highscores():
    if os.path.exists(HIGHSCORES_FILE):
        try:
            with open(HIGHSCORES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_highscores(scores):
    try:
        with open(HIGHSCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Erro salvando highscores:", e)

highscores = load_highscores()  # lista de dicts {name, time_ms}

# ===== Tempo de partida (agora conta para cima) =====
TIME_LIMIT = None  # não usado como limite; usamos timer crescente
time_elapsed_ms = 0

# ===== Helpers para performance / desenhos pré-calculados =====
# pre-calc positions for bottom orb slots (centered)
slots_total = total_orbs if total_orbs > 0 else 4
slot_radius = 14
slot_spacing = slot_radius * 2 + 12
slots_center_x = WIDTH // 2
slots_start_x = slots_center_x - (slot_spacing * slots_total) // 2 + slot_spacing // 2
slots_y = HEIGHT - 40  # centro inferior

# ===== Carrega tela inicial, lobby e créditos =====
start_screen_path = os.path.join("assets", "tela_inicial.png")
try:
    start_img = pygame.image.load(start_screen_path).convert()
    start_img = pygame.transform.scale(start_img, (WIDTH, HEIGHT))
except Exception as e:
    print(f"Aviso: não foi possível carregar tela_inicial.png: {e}")
    start_img = None

lobby_path = os.path.join("assets", "lobby_jogo.jpg")
try:
    lobby_img = pygame.image.load(lobby_path).convert()
    lobby_img = pygame.transform.scale(lobby_img, (WIDTH, HEIGHT))
except Exception as e:
    print(f"Aviso: não foi possível carregar lobby_jogo.jpg: {e}")
    lobby_img = None

credits_path = os.path.join("assets", "tela_creditos.png")
try:
    credits_img = pygame.image.load(credits_path).convert()
    credits_img = pygame.transform.scale(credits_img, (WIDTH, HEIGHT))
except Exception as e:
    print(f"Aviso: não foi possível carregar tela_creditos.png: {e}")
    credits_img = None

# ===== Tela inicial — aguarda espaço para ir à lobby (sem texto) =====
showing_start = True
while showing_start:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                showing_start = False  # vai para lobby
    if start_img:
        window.blit(start_img, (0, 0))
    else:
        window.fill((0, 0, 0))
    pygame.display.update()
    clock.tick(60)

# ===== Lobby: esperar espaço para iniciar jogo, ou 'c' para créditos =====
in_lobby = True
game_started = False
while in_lobby and not game_started:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            raise SystemExit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                game_started = True
                in_lobby = False
            elif event.key == pygame.K_c:
                # abre créditos
                showing_credits = True
                while showing_credits:
                    for ev in pygame.event.get():
                        if ev.type == pygame.QUIT:
                            pygame.quit()
                            raise SystemExit()
                        if ev.type == pygame.KEYDOWN:
                            if ev.key == pygame.K_SPACE:
                                showing_credits = False  # volta ao lobby
                    if credits_img:
                        window.blit(credits_img, (0, 0))
                    else:
                        window.fill((0, 0, 0))
                    pygame.display.update()
                    clock.tick(60)
    if lobby_img:
        window.blit(lobby_img, (0, 0))
    else:
        window.fill((0, 0, 0))
    pygame.display.update()
    clock.tick(60)

# inicia o timer somente quando o jogo começa
start_time = pygame.time.get_ticks()
time_elapsed_ms = 0

# ===== Variáveis para input de nome quando vencer =====
entering_name = False
name_input = ""
name_prompt_font = pygame.font.Font(pygame.font.get_default_font(), 28)

# ===== Função para resetar o jogo =====
def reset_game():
    global player, cam, orbs, collected_orbs, enemies, bullets, start_time
    global game_over, game_won, entering_name, name_input, time_elapsed_ms, enemies_defeated
    # recriar player e câmera
    player = Player(WALL_WIDTH + 100, GROUND_Y - 50)
    cam = Camera(WIDTH, HEIGHT)
    # recriar orbes e reset counters
    orbs = create_orbs(TOTAL_ORBS)
    collected_orbs = 0
    # recriar inimigos (plataformas + chão)
    enemies = create_enemies_on_platforms() + create_ground_enemies(7)
    # limpar tiros
    bullets = []
    enemies_defeated = 0
    # reset flags e timer
    game_over = False
    game_won = False
    entering_name = False
    name_input = ""
    start_time = pygame.time.get_ticks()
    time_elapsed_ms = 0
    

# ===== Loop principal =====
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Quando venceu: tratar input de nome e permitir restart com espaço
        if game_won:
            if entering_name and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    name_input = name_input[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    # salva o score
                    entry = {"name": name_input if name_input.strip() != "" else "Anon", "time_ms": time_elapsed_ms}
                    highscores.append(entry)
                    # ordena por menor tempo
                    highscores = sorted(highscores, key=lambda x: x["time_ms"])[:50]  # guardar top50
                    save_highscores(highscores)
                    entering_name = False
                else:
                    # limitar tamanho e aceitar caracteres normais
                    if len(name_input) < 20 and event.unicode.isprintable():
                        name_input += event.unicode
            elif not entering_name and event.type == pygame.KEYDOWN:
                # após salvar ou se não quiser digitar, espaço reinicia
                if event.key == pygame.K_SPACE:
                    reset_game()
            # ignorar controles normais enquanto venceu
            continue

        # Quando em game_over: permitir restart com espaço
        if game_over:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                reset_game()
            continue

        # controles normais do jogo (quando não venceu e não game_over)
        if not game_over and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.jump_action()
                jump.play()
            if event.key == pygame.K_e:
                bx = player.rect.centerx + (player.facing * 30)
                by = player.rect.centery
                bullets.append(Bullet(bx, by, player.facing))
                tiro.play()
    keys = pygame.key.get_pressed()

    if not game_over and not game_won:
        # atualiza timer crescente
        time_elapsed_ms = pygame.time.get_ticks() - start_time

        player.update(keys, all_platforms, walls)
        cam.update(player.rect, player.vx)

        # Checa colisão jogador <-> orbes (removendo ao coletar)
        for orb in orbs[:]:
            if player.rect.colliderect(orb):
                orbs.remove(orb)
                collected_orbs += 1

        # inimigo <-> jogador: aplica dano apenas se não estiver invulnerável
        for enemy in enemies:
            if enemy.alive and player.rect.colliderect(enemy.rect):
                damaged = player.take_damage()
                if damaged:
                    # play golpe sound when player takes damage
                    if golpe:
                        golpe.play()
                    if player.lives <= 0:
                        game_over = True
                    else:
                        player.vy = 0

        # atualiza inimigos (culling simples: atualiza apenas se próximos à câmera)
        cam_left = int(cam.x) - 200
        cam_right = int(cam.x) + WIDTH + 200
        for enemy in enemies:
            if hasattr(enemy, "dead_finished") and enemy.dead_finished:
                continue
            if enemy.rect.right < cam_left or enemy.rect.left > cam_right:
                continue
            enemy.update()

        # tiros vs inimigos: mata imediatamente (sem animação death por enquanto)
        for bullet in bullets:
            bullet.update()
            for enemy in enemies:
                if getattr(enemy, "alive", True) and bullet.rect.colliderect(enemy.rect):
                    # marca como morto para ambos tipos de inimigo
                    if hasattr(enemy, "start_death"):
                        enemy.start_death()
                    else:
                        enemy.alive = False
                    bullet.alive = False
                    enemies_defeated += 1

        bullets = [b for b in bullets if b.alive]
        enemies = [e for e in enemies if not (hasattr(e, "dead_finished") and e.dead_finished)]

        # Checa vitória ao coletar todas as orbes
        if collected_orbs >= total_orbs and not game_won:
            game_won = True
            entering_name = True
            # trava o tempo final
            time_elapsed_ms = pygame.time.get_ticks() - start_time

    # ===== Desenho =====
    window.fill((35, 60, 110))

    # Desenha background duas vezes para cobrir MAP_WIDTH = 2 * WIDTH (movendo com câmera)
    bg_x = -int(cam.x) % WIDTH
    window.blit(background, (bg_x - WIDTH, -int(cam.y)))
    window.blit(background, (bg_x, -int(cam.y)))

    # Desenha chão (ajustado ao MAP_WIDTH)
    pygame.draw.rect(window, ground_color, (0 - int(cam.x), GROUND_Y - int(cam.y), MAP_WIDTH, GROUND_HEIGHT))

    for plat in all_platforms:
        if plat.right < int(cam.x) - 200 or plat.left > int(cam.x) + WIDTH + 200:
            continue
        pygame.draw.rect(
            window,
            ground_color,
            (plat.x - int(cam.x), plat.y - int(cam.y), plat.width, plat.height),
            border_radius=12
        )

    # Orbes (coletáveis) — desenha se ainda existirem e estiverem na tela
    orb_color = (255, 200, 0)
    for orb in orbs:
        if orb.right < int(cam.x) - 200 or orb.left > int(cam.x) + WIDTH + 200:
            continue
        pygame.draw.circle(window, orb_color, (orb.centerx - int(cam.x), orb.centery - int(cam.y)), orb_radius)

    # Inimigos (desenha apenas os próximos à câmera)
    for enemy in enemies:
        if hasattr(enemy, "dead_finished") and enemy.dead_finished:
            continue
        if enemy.rect.right < int(cam.x) - 200 or enemy.rect.left > int(cam.x) + WIDTH + 200:
            continue
        enemy.draw(window, cam)

    # Tiros
    for bullet in bullets:
        if bullet.rect.right < int(cam.x) - 200 or bullet.rect.left > int(cam.x) + WIDTH + 200:
            continue
        bullet.draw(window, cam)

    # Jogador
    player.draw(window, cam)

    # Desenha paredes laterais (visíveis)
    pygame.draw.rect(window, (60, 60, 60), (left_wall.x - int(cam.x), left_wall.y - int(cam.y), left_wall.width, left_wall.height))
    pygame.draw.rect(window, (60, 60, 60), (right_wall.x - int(cam.x), right_wall.y - int(cam.y), right_wall.width, right_wall.height))

    # ===== HUD: vidas no canto superior esquerdo =====
    heart_radius = 10
    heart_padding = 10
    for i in range(4):  # total de 4 vidas ao todo
        hx = heart_padding + i * (heart_radius * 2 + 8)
        hy = heart_padding + heart_radius
        color = (255, 0, 0) if i < player.lives else (80, 80, 80)
        pygame.draw.circle(window, color, (hx, hy), heart_radius)

    # ===== Timer (contando para cima) =====
    seconds = time_elapsed_ms // 1000
    ms = (time_elapsed_ms % 1000) // 10
    timer_text = font.render(f"Tempo: {seconds:02d}:{ms:02d}", True, (255, 255, 255))
    window.blit(timer_icon, (WIDTH - 210, 10))
    window.blit(timer_text, (WIDTH - 175, 12))

    # ===== Slots de orbes (círculos brancos vazios no centro inferior) - desenha contorno =====
    for i in range(slots_total):
        sx = slots_start_x + i * slot_spacing
        pygame.draw.circle(window, (200, 200, 200), (sx, slots_y), slot_radius, width=3)

    # Preenche os slots coletados (círculos brancos cheios)
    for i in range(collected_orbs):
        if i >= slots_total:
            break
        sx = slots_start_x + i * slot_spacing
        pygame.draw.circle(window, (255, 255, 255), (sx, slots_y), slot_radius - 4)

    ### A parte dedicada ao ranking foi auxiliada com ChatGPT ###

    # ===== Tela de vitória: mostra tempo final e input para nome =====
    if game_won:
        # semi-transparência de fundo
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        window.blit(overlay, (0, 0))

        # mostra tempo final centralizado
        final_seconds = time_elapsed_ms // 1000
        final_ms = (time_elapsed_ms % 1000) // 10
        txt_time = font.render(f"Tempo final: {final_seconds:02d}:{final_ms:02d}", True, (255, 255, 0))
        window.blit(txt_time, (WIDTH//2 - txt_time.get_width()//2, HEIGHT//2 - 80))

        # mostra prompt para nome e caixa
        prompt = name_prompt_font.render("Digite seu nome e pressione Enter:", True, (255,255,255))
        window.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 - 30))

        # desenha caixa de texto
        box_w, box_h = 480, 40
        box_x = WIDTH//2 - box_w//2
        box_y = HEIGHT//2 + 10
        pygame.draw.rect(window, (255,255,255), (box_x-2, box_y-2, box_w+4, box_h+4), border_radius=6)  # borda
        pygame.draw.rect(window, (30,30,30), (box_x, box_y, box_w, box_h), border_radius=6)
        name_surf = name_prompt_font.render(name_input + ("|" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""), True, (255,255,255))
        window.blit(name_surf, (box_x + 10, box_y + (box_h - name_surf.get_height())//2))

        # mostra top 5 do ranking atual (persistente)
        hs_title = font.render("Ranking (melhores tempos)", True, (200,200,255))
        window.blit(hs_title, (50, 100))
        for i, entry in enumerate(highscores[:5]):
            sec = entry["time_ms"] // 1000
            ms_e = (entry["time_ms"] % 1000) // 10
            line = font.render(f"{i+1}. {entry['name']} - {sec:02d}:{ms_e:02d}", True, (220,220,220))
            window.blit(line, (50, 140 + i*28))

        # instrução para reiniciar (após salvar ou pular digitar)
        if not entering_name:
            inst = font.render("Aperte a tecla ESPAÇO para reiniciar", True, (255,255,0))
            window.blit(inst, (WIDTH//2 - inst.get_width()//2, HEIGHT//2 + 70))

    # ===== Tela final (game over) =====
    if game_over:
        # semi-transparência de fundo
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        window.blit(overlay, (0, 0))

        # mensagem GAME OVER
        go_surf = font.render("GAME OVER", True, (255, 0, 0))
        window.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//2 - 40))

        # instrução para reiniciar
        inst2 = font.render("Aperte a tecla ESPAÇO para reiniciar", True, (255, 255, 0))
        window.blit(inst2, (WIDTH//2 - inst2.get_width()//2, HEIGHT//2 + 10))

    pygame.display.update()
    clock.tick(60)

pygame.quit()