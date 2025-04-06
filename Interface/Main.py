import math
import threading
import pygame
import easygui
import dill
import time
from Button import Button
from Label import Label
from TextInput import TextInput
from Dropdown import Dropdown
import serial
from datetime import datetime


# Port of radio
radio_port = "COM5"
radio_baud = 115200
radio_connected = True
radio_serial = None
# last_radio_rx = 0

# Incoming command buffer full of only commands that are enclosed by {}, using "commands" but these
# will be strictly for data recieving and info purposes
command_buffer = []

# lastFrameTime = 0

# Initialize pygame
pygame.init()

BG_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
GRAY = (200, 200, 200)
BLACK = (0, 0, 0)
BLUE = (100, 100, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
PINK = (255, 200, 200)

font_small = pygame.font.Font(None, 12)
font_medium = pygame.font.Font(None, 16)
font_large = pygame.font.Font(None, 20)
font_extra_large = pygame.font.Font(None, 26)
fonts = [font_small, font_medium, font_large, font_extra_large]

# Screen setup
clock = pygame.time.Clock()
WIDTH, HEIGHT = 1800, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Half Badger Test Stand Interface GUI")

# P&ID image setup
pnid = pygame.image.load("Test Stand Code/2025-half-badger-test-stand/Interface/PandID.png")
pnid_center = (1400, 450)
pnid_rect = pnid.get_rect(center=pnid_center)

# Making the valve buttons for manual toggling
valve_names = ["NSV1", "NSV2", "NSV3", "NSV4", "NSV5", "OSV1", "OSV2", "OSV3", "OSV4", "OSV5", "OSV6", "ISV1", "ISV2"]
# valve_index = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] # These get updated according to what's input on the Setup Tab

valve_locations = [(-135, -280, 1), (-30, -310, 0), (-30, -270, 0), (-30, -230, 0), (-30, -190, 0), (-30, -150, 0), (-30, -110, 0), (-30, -70, 0), (-30, -30, 0), (-30, 10, 0), (-30, 50, 0), (-30, 90, 0), (-30, 130, 0)]
valve_buttons = []
valve_override_locations = [(-155, -280, 1), (-30, -290, 0)]
valve_override_buttons = []

# Sensor Update Shit
daq_sensor_type_options = ["PT", "TC_K", "TC_T"]
daq_channel_ids = ["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AIN10", "AIN11", "AIN12", "AIN13"]
daq_sensor_labels = []
daq_sensor_names = []
daq_sensor_type = []
daq_pt_vmin = []
daq_pt_vmax = []
daq_pt_pmax = []
daq_sensor_buttons = []
daq_sensor_button_labels = []
daq_readings_texts = []
daq_readings = [0] * 15 #includes CJC

for id in range(len(daq_channel_ids)):
    daq_sensor_labels.append(Label(daq_channel_ids[id] + ":", 3, 50, id * 40 + 50))
    daq_sensor_names.append(TextInput(125, id * 40 + 45, 3, 100, 30, daq_channel_ids[id]))
    daq_sensor_type.append(Dropdown(250, id * 40 + 45, 50, 30, 3, daq_sensor_type_options))
    daq_pt_vmin.append(TextInput(310, id * 40 + 45, 3, 50, 30, "0"))
    daq_pt_vmax.append(TextInput(370, id * 40 + 45, 3, 50, 30, "5"))
    daq_pt_pmax.append(TextInput(430, id * 40 + 45, 3, 50, 30, "1500"))
    daq_readings_texts.append(Label("No Data", 3, 490, id * 40 + 50))

daq_sensor_labels.append(Label("Channel", 2, 50, 20))
daq_sensor_labels.append(Label("Name", 2, 125, 20))
daq_sensor_labels.append(Label("Type", 2, 250, 20))
daq_sensor_labels.append(Label("Vmin", 2, 310, 20))
daq_sensor_labels.append(Label("Vmax", 2, 370, 20))
daq_sensor_labels.append(Label("Pmax", 2, 430, 20))
daq_sensor_labels.append(Label("Value", 2, 490, 20))

# SEction to say where each servo is plugged into
valve_assign_labels = []
valve_assign_drops = []

valve_assign_labels.append(Label("Valve #", 2, 640, 20))
for i in range(14):
   valve_assign_labels.append(Label(str(i) + ":", 3, 640, i * 40 + 50))
   valve_assign_drops.append(Dropdown(680, i * 40 + 45, 60, 22, 3, (["-"] + valve_names)))

# Button to send all this data
daq_sensor_buttons.append(Button(50, 600, 100, 30, True, (150, 255, 150), GRAY))
daq_sensor_button_labels.append(Label("Send To RPI", 2, 55, 605))



# Command interface
#
# 1: Manually toggle valves, value is held until the valve control is returned to the ECU 
# 14 valves total
# VALVE_INDEX: 0-13, index
# {1,VALVE_INDEX}

# 2: Set which valves are to be under manual control
# 14 valves total
# Send valve index to flip
# {2,VALVE_INDEX}
 
# 3: Configure TC Settings
# 4 TCs
# TC_ID: 0-3
# TYPE: T/K
# {3,TYPE,TC_ID/SENSOR_ID}

# 4: Configure PT
# 

#

#Setting up the valves
for valve_location in valve_locations:
    valve_buttons.append(Button(pnid_center[0] + valve_location[0], pnid_center[1] + valve_location[1],
                                15 if valve_location[2] == 1 else 30, 30 if valve_location[2] == 1 else 15, False,))
    
# for valve_override_location in valve_override_locations:
#     valve_override_buttons.append(Button(pnid_center[0] + valve_override_location[0], pnid_center[1] + valve_override_location[1],
#                                 15 if valve_override_location[2] == 1 else 30, 30 if valve_override_location[2] == 1 else 15, False,
#                                 PINK, GRAY))

# def seconds_since_midnight():
#     # Get the current time
#     now = datetime.now()
    
#     # Calculate the seconds since midnight (00:00)
#     midnight = datetime.combine(now.date(), datetime.min.time())
#     delta = now - midnight
#     return delta.total_seconds()

# Function to read the command including the {} characters
def read_command(ser):
    global last_radio_rx
    buffer = ""
    while True:
      if not radio_connected:
         break
      if ser.in_waiting > 0:
          data = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
          
          if data == "{":
              buffer = ""

          buffer += data
          while '{' in buffer and '}' in buffer:
              start = buffer.find('{')
              end = buffer.find('}', start)
              if end != -1 and end > start:
                  command = buffer[start:end+1]  # Include the {} in the command
                  buffer = buffer[end+1:]
                  command_buffer.append(command)
                  # last_radio_rx = seconds_since_midnight()
                  #print(command)
                  break

# Function to start the reading process in a background thread
def start_reading_radio():
    global radio_connected
    try:
        #ser = serial.Serial(port, baudrate, timeout=2)
        #print(f"Connected to {port}")
        # Start the reading loop in a separate thread
        thread = threading.Thread(target=read_command, args=(radio_serial,), daemon=True)
        thread.start()
        #radio_connected = True
    except serial.SerialException as e:
        #print(f"Failed to connect to {port}: {e}")
        radio_connected = False    

def radio_send(command):
    global radio_connected
    print("SEND", command)
    if radio_connected:
      # cur_time = seconds_since_midnight()
      # start_wait_time = cur_time
      # last_send_time = last_radio_rx

      # while ((cur_time - last_send_time) < 0.2 and (cur_time - start_wait_time) < 2):
      #    cur_time = seconds_since_midnight()
      #    time.sleep(0.01)

      try:
        #print(command)
        radio_serial.write(command.encode())
      except:
        radio_connected = False   

def send_sensor_config():
  global radio_connected

  #Turn the button off
  daq_sensor_buttons[0].is_on = False

  #First we send the names
  names = []
  for text_input in daq_sensor_names:
      names.append(text_input.text)
  command = "{-1," + ",".join(names) + "}"
  radio_out_buffer.append(command)

  #time.sleep(1)

  #The sensor type
  types = []
  for drop in daq_sensor_type:
      types.append(drop.selected)
  command = "{-2," + ",".join(types) + "}"
  radio_out_buffer.append(command)

  #time.sleep(1)

  # Pressure ranges
  pranges = []
  for i in range(len(daq_pt_pmax)):
     pranges.append((0, daq_pt_pmax[i].text))
  formatted_tuples = [f"({','.join(map(str, t))})" for t in pranges]
  command = f"{{-3,{','.join(formatted_tuples)}}}"
  radio_out_buffer.append(command)

  #time.sleep(2)

  # Voltage Ranges
  vranges = []
  for i in range(len(daq_pt_vmin)):
     vranges.append((daq_pt_vmin[i].text, daq_pt_vmax[i].text))
  formatted_tuples = [f"({','.join(map(str, t))})" for t in vranges]
  command = f"{{-4,{','.join(formatted_tuples)}}}"
  radio_out_buffer.append(command)

  #time.sleep(1)


def find_valve_index(name):
    for i, valve in enumerate(valve_assign_drops):
      if valve.selected == name:
         return i
  
    return -1

def drawScreen(screen):
    screen.blit(pnid, pnid_rect)

    for button in valve_buttons:
        button.draw(screen)
    for button in valve_override_buttons:
        button.draw(screen)
    for label in daq_sensor_labels:
        label.draw(screen, fonts)
    for text in daq_sensor_names:
        text.draw(screen, fonts)
    for drop in range(len(daq_sensor_type)-1, -1, -1):
        daq_sensor_type[drop].draw(screen, fonts)
    for sensor in daq_pt_vmin:
        sensor.draw(screen, fonts)
    for sensor in daq_pt_vmax:
        sensor.draw(screen, fonts)
    for sensor in daq_pt_pmax:
        sensor.draw(screen, fonts)
    for button in daq_sensor_buttons:
        button.draw(screen)
    for label in daq_sensor_button_labels:
        label.draw(screen, fonts)
    for text in daq_readings_texts:
        text.draw(screen, fonts)
    for label in valve_assign_labels:
        label.draw(screen, fonts)
    for drop in range(len(valve_assign_drops)-1,-1,-1):
        valve_assign_drops[drop].draw(screen, fonts)


    pass

def sigfig_round(x, sig):
    return round(x, sig - int(math.floor(math.log10(abs(x)))) - 1)

def parse_state_string(s):
    # Remove the braces and split by comma
    items = s.strip('{}').split(',')
    # Convert to integers, skipping the first item
    state_list = []
    for item in items[1:]:
      try:
         state_list.append(int(item))
      except:
         pass
    return state_list

radio_out_buffer = []

# Main GUI loop
running = True
while running:
    # Connecting to the radio
    if (not radio_connected) or radio_serial == None:
        try:
          radio_serial = serial.Serial(radio_port, radio_baud, timeout=2)
          radio_connected = True
          start_reading_radio()
        except:
          radio_connected = False


    screen.fill(BG_COLOR)  # Clear the screen

    # Event handling
    valve_updates = [0] * 14
    valve_override_updates = [0] * 14

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        for i_button in range(len(valve_buttons)):
            valve_index = find_valve_index(valve_names[i_button])

            if valve_index >= 0:
                valve_updates[valve_index] = valve_buttons[i_button].handle_event(event)
            

        for i_button in range(len(valve_override_buttons)):
            if len(valve_override_updates) < len(valve_override_buttons):
              valve_override_updates.append(valve_override_buttons[i_button].handle_event(event))
            else:
              valve_override_updates[i_button] += valve_override_buttons[i_button].handle_event(event)

        for sensor in daq_sensor_names:
           sensor.handle_event(event)
        for sensor in daq_pt_pmax:
           sensor.handle_event(event)
        for sensor in daq_pt_vmax:
           sensor.handle_event(event)
        for sensor in daq_pt_vmin:
           sensor.handle_event(event)

        for drop in daq_sensor_type:
           drop.handle_event(event)

        for drop in valve_assign_drops:
           drop.handle_event(event)

        for i_button in range(len(daq_sensor_buttons)):
           hit = daq_sensor_buttons[i_button].handle_event(event)

           if hit == 1 and i_button == 0:
              drawScreen(screen)
              pygame.display.flip()
              send_sensor_config()

    #command_buffer = ["{-7,187.65491956472397,-204.44412901997566,-387.9949062466621,-605.0885435342788,-829.7873514890671,-1015.101374745369,-1215.3105375766752,-1371.9635581970215,-1532.914491891861,-1588.3246221542358,-1588.3383815288544,-1588.3388571739195,-1588.3324513435364,28.931032069570122,21.80409868538385}"]

    # Processing the incoming commands from RPI
    for command in command_buffer:
      print(command)
       # -7 => new DAQ data
      if command.startswith("{-7,"):
          try:
             daq_readings = list(map(float, command.strip("{").strip("}").split(",")[1:]))
             for i_text in range(len(daq_readings_texts)):
                daq_readings_texts[i_text].text = str(sigfig_round(daq_readings[i_text],4))
          except:
            pass
          

      if command.startswith("{1,"):
          states = parse_state_string(command)
          if len(states) == 14:
             for i, button in enumerate(valve_buttons):
                button.is_on = states[i] == 1

    # command_buffer = []

    #Drawing screen
    drawScreen(screen)

    # frameTime = seconds_since_midnight()
    # if (math.floor(frameTime) - math.floor(lastFrameTime)) > 2.5:
          #radio_send("{0," + str(1 + len(radio_out_buffer)) + "}")

          # for com in radio_out_buffer:
          #    radio_send(com)

          # radio_send("{-5}")

          # lastFrameTime = frameTime
          # time.sleep(0.5)

          # radio_out_buffer = []

    #Printing commands I want to send
    
    if(sum(valve_updates) > 0):         
      SEND#radio_out_buffer.append("{1," + str(valve_updates.index(1)) + "}")
    if sum(valve_override_updates) > 0:
      SEND#radio_out_buffer.append("{2," + str(valve_override_updates.index(1)) + "}")

    # Draw updates
    pygame.display.flip()  # Update the display
    clock.tick(60)

# Cleanup
pygame.quit()