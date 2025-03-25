import pygame
from Node import Node

# Initialize pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 1600, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Draggable Rectangle with Dropdowns")

# # Colors
WHITE = (255, 255, 255)
# GRAY = (200, 200, 200)
# BLACK = (0, 0, 0)
# BLUE = (200, 200, 255)


canvas_dragging = False
canvas_origin = [0, 0]
canvas_drag_start = [0, 0]
scale = 1

def update_canvas(event, nodes):
    global canvas_dragging
    global canvas_origin
    global canvas_drag_start
    global scale

    if event.type == pygame.MOUSEBUTTONDOWN:
        canvas_dragging = True
        canvas_drag_start = [event.pos[0], event.pos[1]]
    elif event.type == pygame.MOUSEBUTTONUP:
        canvas_dragging = False
    elif event.type == pygame.MOUSEMOTION and canvas_dragging:
        delta_x = event.pos[0] - canvas_drag_start[0]
        delta_y = event.pos[1] - canvas_drag_start[1]

        canvas_origin[0] = canvas_origin[0] + delta_x
        canvas_origin[1] = canvas_origin[1] + delta_y

        canvas_drag_start = [event.pos[0], event.pos[1]]

        for node in nodes:  
          node.move(delta_x, delta_y)
          node.draw(screen, scale)

    elif event.type == pygame.MOUSEWHEEL:
        prev_scale = scale
        scale = scale + scale * 0.05 * event.y
        delta_scale = scale / prev_scale - 1
        mouse_pos = pygame.mouse.get_pos()

        for node in nodes:
            delta_x = (node.rect.x - mouse_pos[0]) * delta_scale
            delta_y = (node.rect.y - mouse_pos[1]) * delta_scale

            node.move(delta_x, delta_y)
            node.scale(event, delta_scale)
            node.draw(screen, scale)

      
# Main loop
clock = pygame.time.Clock()

running = True
nodes = [Node(300, 200)]

for node in nodes:
    node.draw(screen, 1)

while running:
    screen.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        node_hit = False

        for node in nodes:
            node_hit = node.handle_event(event)
            if node_hit:
                break

        if event.type == pygame.KEYDOWN:
          if event.key == pygame.K_n:
              mouse = pygame.mouse.get_pos()
              nodes.append(Node(mouse[0], mouse[1]))

        #Move screen in no nodes were pressed
        if not node_hit:
            update_canvas(event, nodes)

    for node in nodes:
      node.draw(screen, scale)
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
