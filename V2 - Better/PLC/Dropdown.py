import pygame

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
LIGHT_GRAY = (240, 240, 240)
BLACK = (0, 0, 0)
BLUE = (100, 100, 255)

class Dropdown:
    """ A simple dropdown menu inside a draggable rectangle """

    def __init__(self, x, y, width, height, fonts, font, options):
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.options = options
        self.selected = options[0]
        self.expanded = False
        #self.font_height = font_height
        #self.fonts = fonts
        self.font = font #pygame.font.Font(None, font_height)

    def draw(self, surface, fonts):
        pygame.draw.rect(surface, WHITE if self.expanded else GRAY, self.rect, border_radius=5)
        pygame.draw.rect(surface, BLACK, self.rect, 1)
        text = fonts[self.font].render(self.selected, True, BLACK)
        surface.blit(text, (self.rect.x + 5, self.rect.y + 5))

        if self.expanded:
            for i, option in enumerate(self.options):
                option_rect = pygame.Rect(self.rect.x, self.rect.y + (i + 1) * self.rect.height, self.rect.width, self.rect.height)
                pygame.draw.rect(surface, LIGHT_GRAY, option_rect, border_radius=5)
                pygame.draw.rect(surface, BLACK, option_rect, 1)
                text = fonts[self.font].render(option, True, BLACK)
                surface.blit(text, (option_rect.x + 5, option_rect.y + 2))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.expanded = not self.expanded
            elif self.expanded:
                for i, option in enumerate(self.options):
                    option_rect = pygame.Rect(self.rect.x, self.rect.y + (i + 1) * self.rect.height, self.rect.width, self.rect.height)
                    if option_rect.collidepoint(event.pos):
                        self.selected = option
                        self.expanded = False
                        break
                else:
                    self.expanded = False