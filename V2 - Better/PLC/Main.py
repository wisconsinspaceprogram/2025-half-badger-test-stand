import pygame
import easygui
import dill
import time
from Node import Node

# Initialize pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 1400, 750
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Half Badger GUI PLC")

# # Colors
WHITE = (255, 255, 255)
# GRAY = (200, 200, 200)
# BLACK = (0, 0, 0)
# BLUE = (200, 200, 255)

SENSOR_OPTIONS = ["-", "PT_N", "PT_LOX", "PT_LOX_CAV", "PT_IPA", "PT_TCA", "TC_N", "TC_LOX", 
                  "TC_LOX_CAV", "TC_TCA1", "TC_TCA2", "TC_IPA", "T_STATE", "T_COM", "COMMAND"]

OPERATION_OPTIONS = ["-", "<", ">", "="]


canvas_dragging = False
canvas_origin = [0, 0]
canvas_drag_start = [0, 0]
scale = 1

font_small = pygame.font.Font(None, 12)
font_medium = pygame.font.Font(None, 16)
font_large = pygame.font.Font(None, 20)
fonts = [font_small, font_medium, font_large]

def draw_all(scale):
  screen.fill(WHITE)
  for node in nodes:
    node.draw(screen, scale, fonts)   

def update_canvas(event, nodes):
    global canvas_dragging
    global canvas_origin
    global canvas_drag_start
    global scale
    global fonts

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

        font_small = pygame.font.Font(None, int(12*scale))
        font_medium = pygame.font.Font(None, int(16*scale))
        font_large = pygame.font.Font(None, int(20*scale))
        fonts = [font_small, font_medium, font_large]
  
      

# Open a file save dialog (to select both directory and filename)
# file_path = easygui.filesavebox(title="Select File to Save Data", default="*.txt")

 

# Main loop
clock = pygame.time.Clock()

running = True
nodes = [Node(600, 150, SENSOR_OPTIONS, OPERATION_OPTIONS, fonts)]

draw_all(1)


while running:
    

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
              new_node = Node(mouse[0], mouse[1], SENSOR_OPTIONS, OPERATION_OPTIONS, fonts)
              new_node.draw(screen, scale, fonts)
              nodes.append(new_node)
          
          if event.key == pygame.K_s:
              save_path = easygui.filesavebox(title="Select File to Save State Data to", default="")

              state_numbers = []
              state_change_operations = []
              state_change_sensor_id = []
              state_change_threshold_values = []
              state_change_num_sensors = []
              state_change_physical_state = []
              to_state_numbers = []

              if save_path != None:
                for node in nodes:
                    state_numbers.append(node.get_state_number())
                    state_change_operations.append(node.get_operations())
                    state_change_sensor_id.append(node.get_sensor_ids())
                    state_change_threshold_values.append(node.get_thresholds())
                    state_change_num_sensors.append(node.get_num_sensors())
                    state_change_physical_state.append(node.get_physical_state_dict())
                    to_state_numbers.append(node.get_to_states())


                    #process out invalid stuff and get mad if there are any issues!!!


                out_dict = {'numbers': state_numbers, 'toNumbers': to_state_numbers, 'operations':state_change_operations, 'ids':state_change_sensor_id, 
                                'thresholds':state_change_threshold_values, 'num_sensors':state_change_num_sensors, 'nodes':nodes, 'physical':state_change_physical_state}
                    
                if not save_path.endswith(".pkl"):
                   save_path += '.pkl'

                with open(save_path, 'wb') as pickle_file:
                  dill.dump(out_dict, pickle_file)
                
                print("Saved as " + save_path)
              else:
                print("Bad file path, DID NOT SAVE!!!")
          
          if event.key == pygame.K_o:
            open_path = easygui.fileopenbox("State Data to open")

            if open_path != None:
              with open(open_path, "rb") as file:
                loaded_data = dill.load(file)
                nodes = loaded_data["nodes"]

              #print(save_path)

        #Move screen in no nodes were pressed
        if not node_hit:
            update_canvas(event, nodes)

    # for node in nodes:
    #   node.draw(screen, scale)
    draw_all(scale)
    pygame.display.flip()
    clock.tick(60)

    #print(len(nodes))

pygame.quit()
