import pygame

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (100, 100, 255)

class TextInput:
    """ A simple text input field """
    
    def __init__(self, x, y, fonts, font, width=100, height=30):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.width = width
        self.height = height
        self.active = False
        #self.font_height = font_height
        self.fonts = fonts
        self.font = font#pygame.font.Font(None, font_height)

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE if self.active else GRAY, self.rect, border_radius=5)
        pygame.draw.rect(surface, BLACK, self.rect, 1)
        text_surface = self.fonts[self.font].render(self.text, True, BLACK)
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False  # Press Enter to confirm input
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]  # Delete last character
            else:
                self.text += event.unicode  # Add character
