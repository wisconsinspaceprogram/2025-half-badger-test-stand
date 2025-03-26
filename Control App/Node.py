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

class Node:
    """ A draggable rectangle with a label and dropdowns """
    
    def __init__(self, x, y, SENSOR_OPTIONS, OPERATION_OPTIONS, fonts):
        self.SENSOR_OPTIONS = SENSOR_OPTIONS
        self.OPERATION_OPTIONS = OPERATION_OPTIONS
        self.height = 450
        self.width = 230
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
        
        # region Valve Buttons
        # Top state label
        self.labels.append(Label("State # ", fonts, 2, 0, 0))
        self.label_loc.append((5,8))

        self.texts.append(TextInput(0,0,fonts, 2,30,17))
        self.text_loc.append((50, 5))

        # Valve buttons
        # Column 1
        self.labels.append(Label("NSV1:", fonts, 0, 0, 0))
        self.labels.append(Label("NSV2:", fonts, 0, 0, 0))
        self.labels.append(Label("NSV3:", fonts, 0, 0, 0))
        self.labels.append(Label("NSV4:", fonts, 0, 0, 0))
        self.labels.append(Label("NSV5:", fonts, 0, 0, 0))
        self.label_loc.append((10,30))
        self.label_loc.append((10,45))
        self.label_loc.append((10,60))
        self.label_loc.append((10,75))
        self.label_loc.append((10,90))

        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.button_loc.append((45,30))
        self.button_loc.append((45,45))
        self.button_loc.append((45,60))
        self.button_loc.append((45,75))
        self.button_loc.append((45,90))

        # Column 2
        self.labels.append(Label("ISV1:", fonts, 0, 0, 0))
        self.labels.append(Label("ISV2:", fonts, 0, 0, 0))
        self.labels.append(Label("OSV1:", fonts, 0, 0, 0))
        self.labels.append(Label("OSV2:", fonts, 0, 0, 0))
        self.labels.append(Label("OSV3:", fonts, 0, 0, 0))
        self.label_loc.append((75,30))
        self.label_loc.append((75,45))
        self.label_loc.append((75,60))
        self.label_loc.append((75,75))
        self.label_loc.append((75,90))

        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.button_loc.append((110,30))
        self.button_loc.append((110,45))
        self.button_loc.append((110,60))
        self.button_loc.append((110,75))
        self.button_loc.append((110,90))

        # Column 3
        self.labels.append(Label("OSV4:", fonts, 0, 0, 0))
        self.labels.append(Label("OSV5:", fonts, 0, 0, 0))
        self.labels.append(Label("OSV6:", fonts, 0, 0, 0))
        self.labels.append(Label("PYRO1:", fonts, 0, 0, 0))
        self.labels.append(Label("PYRO2:", fonts, 0, 0, 0))
        self.label_loc.append((140,30))
        self.label_loc.append((140,45))
        self.label_loc.append((140,60))
        self.label_loc.append((140,75))
        self.label_loc.append((140,90))

        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.buttons.append(Button(50, 50, 20, 10))
        self.button_loc.append((185,30))
        self.button_loc.append((185,45))
        self.button_loc.append((185,60))
        self.button_loc.append((185,75))
        self.button_loc.append((185,90))

        # endregion

        # region Set 1
        y_base = 110
        # Top state label
        self.labels.append(Label("Change Set 1, min required:", fonts, 1, 0, 0))
        self.label_loc.append((5,y_base))

        self.texts.append(TextInput(0,0,fonts, 1, 30, 15))
        self.text_loc.append((180, y_base-2))

        #Row 1
        for i in range(6):
          self.dropdowns.append(Dropdown(0, 0, 70, 14, fonts, 0, SENSOR_OPTIONS))
          self.dropdown_loc.append((5, y_base + 15 + i * 15))

          self.dropdowns.append(Dropdown(0, 0, 20, 14, fonts, 0, OPERATION_OPTIONS))
          self.dropdown_loc.append((80, y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts, 0,45,14))
          self.text_loc.append((105, y_base + 15 + i * 15))

          self.labels.append(Label("=>", fonts,0, 0, 0))
          self.label_loc.append((160,y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts,0,45,14))
          self.text_loc.append((180, y_base + 15 + i * 15))

        # endregion

        # region Set 2
        y_base = 220
        # Top state label
        self.labels.append(Label("Change Set 2, min required:", fonts, 1, 0, 0))
        self.label_loc.append((5,y_base))

        self.texts.append(TextInput(0,0,fonts, 1, 30, 15))
        self.text_loc.append((180, y_base-2))

        #Row 1
        for i in range(6):
          self.dropdowns.append(Dropdown(0, 0, 70, 14, fonts, 0, SENSOR_OPTIONS))
          self.dropdown_loc.append((5, y_base + 15 + i * 15))

          self.dropdowns.append(Dropdown(0, 0, 20, 14, fonts, 0, OPERATION_OPTIONS))
          self.dropdown_loc.append((80, y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts, 0,45,14))
          self.text_loc.append((105, y_base + 15 + i * 15))

          self.labels.append(Label("=>", fonts,0, 0, 0))
          self.label_loc.append((160,y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts,0,45,14))
          self.text_loc.append((180, y_base + 15 + i * 15))

        # endregion

        # region Set 3
        y_base = 330
        # Top state label
        self.labels.append(Label("Change Set 3, min required:", fonts, 1, 0, 0))
        self.label_loc.append((5,y_base))

        self.texts.append(TextInput(0,0,fonts, 1, 30, 15))
        self.text_loc.append((180, y_base-2))

        #Row 1
        for i in range(6):
          self.dropdowns.append(Dropdown(0, 0, 70, 14, fonts, 0, SENSOR_OPTIONS))
          self.dropdown_loc.append((5, y_base + 15 + i * 15))

          self.dropdowns.append(Dropdown(0, 0, 20, 14, fonts, 0, OPERATION_OPTIONS))
          self.dropdown_loc.append((80, y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts, 0,45,14))
          self.text_loc.append((105, y_base + 15 + i * 15))

          self.labels.append(Label("=>", fonts,0, 0, 0))
          self.label_loc.append((160,y_base + 15 + i * 15))

          self.texts.append(TextInput(0,0,fonts,0,45,14))
          self.text_loc.append((180, y_base + 15 + i * 15))

        # endregion

    def draw(self, surface, scale, fonts):
        self.rect.height = self.height * scale
        self.rect.width = self.width * scale
        self.fonts = fonts
        pygame.draw.rect(surface, BLUE, self.rect, border_radius=10)

        # setting the locations of everything in the node
        if len(self.dropdowns) > 0:
          for i, dropdown in enumerate(self.dropdowns):
              dropdown.fonts = self.fonts
              dropdown.rect.x = self.rect.x + self.dropdown_loc[i][0] * scale
              dropdown.rect.y = self.rect.y + self.dropdown_loc[i][1] * scale
              dropdown.rect.height = dropdown.height * scale
              dropdown.rect.width = dropdown.width * scale
              #dropdown.font = pygame.font.Font(None, int(dropdown.font_height * scale))

        if len(self.texts) > 0:
          for i, text in enumerate(self.texts):
              text.fonts = self.fonts
              text.rect.x = self.rect.x + self.text_loc[i][0] * scale
              text.rect.y = self.rect.y + self.text_loc[i][1] * scale
              text.rect.height = text.height * scale
              text.rect.width = text.width * scale
              text.rect.width = text.width * scale
              #text.font = pygame.font.Font(None, int(text.font_height * scale))
              text.draw(surface)
        
        if len(self.labels) > 0:
          for i, label in enumerate(self.labels):
              label.fonts = self.fonts
              label.x = self.rect.x + self.label_loc[i][0] * scale
              label.y = self.rect.y + self.label_loc[i][1] * scale
              label.draw(surface)
              #label.font = pygame.font.Font(None, int(label.font_height * scale))
        
        if len(self.buttons) > 0:
            for i, button in enumerate(self.buttons):
                button.x = self.rect.x + self.button_loc[i][0] * scale
                button.y = self.rect.y + self.button_loc[i][1] * scale
                button.rect = pygame.Rect(button.x, button.y, button.width * scale, button.height * scale)
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