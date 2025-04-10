import pygame

# Colors

class Button:
    """ A simple on/off toggle button or checkbox """

    def __init__(self, x, y, width=100, height=40, auto_re_draw=True, on_col=(0,255,0), off_col=(255,0,0)):
        self.height = height
        self.width = width
        self.rect = pygame.Rect(x, y, width, height)
        self.is_on = False  # Initially off
        self.auto_re_draw = auto_re_draw
        self.on_col = on_col
        self.off_col = off_col

    def draw(self, surface):
        # Draw the button with green if on, red if off
        color = self.on_col if self.is_on else self.off_col
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        #pygame.draw.rect(surface, BLACK, self.rect, 2)  # Button border
        #self.label.text = "On" if self.is_on else "Off"  # Update the label text
        #self.label.draw(surface)  # Draw the label next to the button

    def handle_event(self, event):
        hit = 0
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                hit = 1
                if self.auto_re_draw:
                    self.is_on = not self.is_on  # Toggle the button state
        return hit
    
    def force_on(self):
        self.is_on = True
    
    def forcee_off(self):
        self.is_on = False
                