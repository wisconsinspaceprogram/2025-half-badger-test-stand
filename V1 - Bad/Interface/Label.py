import pygame

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (100, 100, 255)

class Label:
    """ A simple wrapper class for displaying text at a specified position """

    def __init__(self, text, font, x, y):
        self.text = text
        self.x = x
        self.y = y
        #self.font_height = font_height
        self.font = font
        #self.fonts = fonts#pygame.font.Font(None, font_height)

    def draw(self, surface, fonts):
        text_surface = fonts[self.font].render(self.text, True, BLACK)
        surface.blit(text_surface, (self.x, self.y))