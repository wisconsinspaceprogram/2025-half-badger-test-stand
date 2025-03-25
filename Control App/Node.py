import pygame
from Dropdown import Dropdown
from Label import Label
from TextInput import TextInput
from Button import Button

# Colors
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (200, 200, 255)

# Dropdown options
dropdown_options = [
    ["PT_LOX_TANK", "PT_IPA_TANK", "TC_TCA", "TMIE_IN_STATE", "TIME_LAST_MESSAGE"],
    ["<", ">"],
    ["Choice X", "Choice Y", "Choice Z"]
]

class Node:
    """ A draggable rectangle with a label and dropdowns """
    
    def __init__(self, x, y):
        self.height = 500
        self.width = 300
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.dragging = False        

        # elements setup
        self.label_loc = []
        self.text_loc = []
        self.dropdown_loc = []
        self.button_loc = []

        self.labels = []
        self.texts = []
        self.dropdowns = []
        self.buttons = []
        
        # Top state label
        self.labels.append(Label("State: ", 20, 0, 0))
        self.label_loc.append((5,8))

        self.texts.append(TextInput(0,0,20,30,17))
        self.text_loc.append((45, 5))

        self.buttons.append(Button(50, 50, 10, 10))
        self.button_loc.append((50,50))
      
        # for i in range(3):
        #     self.dropdowns.append(Dropdown(0, 0, 50, 20, 14, dropdown_options[i]))
        #     self.texts.append(TextInput(0, 0, 14, 50, 20))

    def draw(self, surface, scale):
        self.rect.height = self.height * scale
        self.rect.width = self.width * scale
        
        pygame.draw.rect(surface, BLUE, self.rect, border_radius=10)

        # setting the locations of everything in the node
        if len(self.dropdowns) > 0:
          for i, dropdown in enumerate(self.dropdowns):
              dropdown.rect.x = self.rect.x + self.dropdown_loc[i][0] * scale
              dropdown.rect.y = self.rect.y + self.dropdown_loc[i][1] * scale
              dropdown.rect.height = dropdown.height * scale
              dropdown.rect.width = dropdown.width * scale
              dropdown.font = pygame.font.Font(None, int(dropdown.font_height * scale))

        if len(self.texts) > 0:
          for i, text in enumerate(self.texts):
              text.rect.x = self.rect.x + self.text_loc[i][0] * scale
              text.rect.y = self.rect.y + self.text_loc[i][1] * scale
              text.rect.height = text.height * scale
              text.rect.width = text.width * scale
              text.rect.width = text.width * scale
              text.font = pygame.font.Font(None, int(text.font_height * scale))
        
        if len(self.labels) > 0:
          for i, label in enumerate(self.labels):
              label.x = self.rect.x + self.label_loc[i][0] * scale
              label.y = self.rect.y + self.label_loc[i][1] * scale
              label.font = pygame.font.Font(None, int(label.font_height * scale))
        
        if len(self.buttons) > 0:
            for i, button in enumerate(self.buttons):
                button.x = self.rect.x + self.button_loc[i][0] * scale
                button.y = self.rect.y + self.button_loc[i][1] * scale
                button.rect = pygame.Rect(button.x, button.y, button.width * scale, button.height * scale)

        # drawing it all
        for text in self.texts:
            text.draw(surface)
        for label in self.labels:
            label.draw(surface)
        for button in self.buttons:
            button.draw(surface)

        #double drawing the expanded dropdown so it's always on top
        highlight_drop = None
        for dropdown in self.dropdowns:
            dropdown.draw(surface)
            if dropdown.expanded:
                highlight_drop = dropdown
        if highlight_drop != None:
            highlight_drop.draw(surface)

    def handle_event(self, event):
        hit = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.dragging = True
                self.offset_x = event.pos[0] - self.rect.x
                self.offset_y = event.pos[1] - self.rect.y
                hit = True
        
        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False
            if self.rect.collidepoint(event.pos):
                hit = True
        
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                self.rect.x = event.pos[0] - self.offset_x
                self.rect.y = event.pos[1] - self.offset_y

                hit = True

        for dropdown in self.dropdowns:
            dropdown.handle_event(event)

        for text in self.texts:
            text.handle_event(event)

        for button in self.buttons:
            button.handle_event(event)

        return hit

    def scale(self, event, delta_scale):
        self.rect.width *= (delta_scale + 1)
        self.rect.height *= (delta_scale + 1)

    def move(self, delta_x, delta_y):
        self.rect.x += delta_x
        self.rect.y += delta_y