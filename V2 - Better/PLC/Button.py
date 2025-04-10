import pygame
from Label import Label

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (100, 100, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0, 50)

class Button:
    """ A simple on/off toggle button or checkbox """

    def __init__(self, x, y, width=100, height=40):
        self.height = height
        self.width = width
        self.rect = pygame.Rect(x, y, width, height)
        self.is_on = False  # Initially off
        #self.font_height = 30
        #self.label = Label("Off", self.font_height, x + width + 10, y + 10)

    def draw(self, surface):
        # Draw the button with green if on, red if off
        color = GREEN if self.is_on else RED
        pygame.draw.rect(surface, color, self.rect, border_radius=2)
        #pygame.draw.rect(surface, BLACK, self.rect, 2)  # Button border
        #self.label.text = "On" if self.is_on else "Off"  # Update the label text
        #self.label.draw(surface)  # Draw the label next to the button

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.is_on = not self.is_on  # Toggle the button state
                