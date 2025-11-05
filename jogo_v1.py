# ===== Inicialização =====
# ----- Importa e inicia pacotes
import pygame

pygame.init()

# ----- Gera tela principal
WIDTH, HEIGHT = 1280, 720
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Nome do jogo')

# ----- Classe do personagem
class Player:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.color = (255, 0, 0)
        self.vx = 0
        self.vy = 0
        self.speed = 5
        self.jump = -15
        self.on_ground = True

    def update(self, keys):
        # Movimento lateral
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # Aplicação simples de pulo
        self.rect.y += self.vy
        if not self.on_ground:
            self.vy += 1  # gravidade simples fixa

        # "Chão" fixo
        if self.rect.y >= 670:  # 720 - altura (50)
            self.rect.y = 670
            self.vy = 0
            self.on_ground = True

    def jump_action(self):
        if self.on_ground:
            self.vy = self.jump
            self.on_ground = False

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)

# ----- Inicia estruturas de dados
game = True
clock = pygame.time.Clock()
player = Player(100, 670)

# ===== Loop principal =====
while game:
    # ----- Trata eventos
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            game = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                player.jump_action()

    # ----- Atualiza estado
    keys = pygame.key.get_pressed()
    player.update(keys)

    # ----- Gera saídas
    window.fill((0, 0, 255))  # Fundo azul
    player.draw(window)

    # ----- Atualiza estado do jogo
    pygame.display.update()  # Mostra o novo frame
    clock.tick(60)

# ===== Finalização =====
pygame.quit()  # Função do PyGame que finaliza os recursos utilizados