import pygame
import sys

def mostrar_tela_final(window, background, font, collected_orbs, total_orbs):
    """Exibe a tela final e retorna 'voltar' ou 'sair' conforme ação do jogador."""

    WIDTH, HEIGHT = window.get_size()

    # Mensagem baseada nas orbes coletadas
    if collected_orbs == total_orbs:
        mensagem = "Você coletou todas as orbes!"
    elif collected_orbs >= total_orbs // 2:
        mensagem = f"Você coletou {collected_orbs}/{total_orbs} orbes. A floresta está se recuperando!"
    elif collected_orbs > 0:
        mensagem = f"Você coletou {collected_orbs}/{total_orbs} orbes. Ainda há esperança..."
    else:
        mensagem = "Nenhuma orbe coletada... Boa sorte na próxima"

    # Cria um leve fade-in
    fade_surface = pygame.Surface((WIDTH, HEIGHT))
    fade_surface.fill((0, 0, 0))
    for alpha in range(0, 180, 5):
        window.blit(background, (0, 0))
        fade_surface.set_alpha(alpha)
        window.blit(fade_surface, (0, 0))
        pygame.display.update()
        pygame.time.delay(20)

    # Retângulo arredondado central
    rect_w, rect_h = 800, 250
    rect_x = (WIDTH - rect_w) // 2
    rect_y = (HEIGHT - rect_h) // 2
    rect_color = (30, 30, 30, 200)

    box_surface = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
    pygame.draw.rect(box_surface, rect_color, (0, 0, rect_w, rect_h), border_radius=25)

    # Textos
    titulo = font.render("Fim da Jornada", True, (255, 255, 255))
    texto = font.render(mensagem, True, (220, 220, 220))
    dica1 = font.render("Pressione ESPAÇO para jogar novamente", True, (180, 180, 180))
    dica2 = font.render("Pressione ESC para sair", True, (150, 150, 150))

    # Desenha tudo
    window.blit(background, (0, 0))
    window.blit(box_surface, (rect_x, rect_y))
    window.blit(titulo, (WIDTH//2 - titulo.get_width()//2, rect_y + 40))
    window.blit(texto, (WIDTH//2 - texto.get_width()//2, rect_y + 110))
    window.blit(dica1, (WIDTH//2 - dica1.get_width()//2, rect_y + rect_h - 80))
    window.blit(dica2, (WIDTH//2 - dica2.get_width()//2, rect_y + rect_h - 40))
    pygame.display.update()

    # Espera o jogador escolher
    esperando = True
    while esperando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    return "voltar"  # volta para o jogo
                if event.key == pygame.K_ESCAPE:
                    return "sair"  # sai do jogo
        pygame.time.delay(50)