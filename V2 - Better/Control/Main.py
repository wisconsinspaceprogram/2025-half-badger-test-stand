import math
import queue
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
from queue import Queue, Empty
from labjack import ljm
from statistics import mean
import u6


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
pnid = pygame.image.load("Test Stand Code/2025-half-badger-test-stand/V2 - Better/Control/PandID.png")
pnid_center = (1400, 450)
pnid_rect = pnid.get_rect(center=pnid_center)

# Making the valve buttons for manual toggling
valve_names = ["NSV1", "NSV2", "NSV3", "NSV4", "NSV5", "OSV1", "OSV2", "OSV3", "OSV4", "OSV5", "OSV6", "ISV1", "ISV2"]
valve_index = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] 

valve_locations = [(-135, -280, 1), (-30, -310, 0), (-120, 200, 0), (-70, 370, 0), (70, -50, 0), (-90, -260, 0), (-50, 60, 0), (150, 50, 0), (170, 75, 0), (-160, 10, 0), (-210, -40, 0), (40, 280, 0), (175, 240, 0)]
valve_buttons = []
valve_override_locations = [(-155, -280, 1), (-30, -290, 0)]
valve_override_buttons = []

# Sensor Update Shit
T7_channel_ids = ["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AIN10", "AIN11", "AIN12", "AIN13"]
T7_sensor_types = ["PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "TC_T"]
T7_pt_pressure_ranges = [(0, 1500)] * 14
T7_pt_voltage_ranges = [(0, 10)] * 14

T7_pt_pressure_ranges[0] = (0,100)
T7_pt_voltage_ranges[0] = (0.5,5)

T7_sensor_labels = []
T7_sensor_names = []
T7_readings_texts = []
T7_readings = [0] * 15 #includes CJC

for id in range(len(T7_channel_ids)):
    T7_sensor_labels.append(Label(T7_channel_ids[id] + ":", 3, 50, id * 40 + 80))
    T7_sensor_names.append(TextInput(125, id * 40 + 75, 3, 100, 30, T7_channel_ids[id]))
    T7_readings_texts.append(Label("No Data", 3, 250, id * 40 + 80))

T7_sensor_labels.append(Label("CJC:", 3, 50, 14 * 40 + 80))
T7_readings_texts.append(Label("No Data", 3, 250, 14 * 40 + 80))

T7_sensor_labels.append(Label("Channel", 2, 50, 50))
T7_sensor_labels.append(Label("Name", 2, 125, 50))
T7_sensor_labels.append(Label("Value", 2, 250, 50))
T7_sensor_labels.append(Label("T7 DAQ", 3, 50, 25))

U6_channel_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
U6_sensor_types = ["TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_K", "TC_T"]
U6_pt_pressure_ranges = [(0, 1500)] * 14
U6_pt_voltage_ranges = [(0, 10)] * 14

U6_sensor_labels = []
U6_sensor_names = []
U6_readings_texts = []
U6_readings = [0] * 15 #includes CJC

for id in range(len(U6_channel_ids)):
    U6_sensor_labels.append(Label("AIN" + str(U6_channel_ids[id]) + ":", 3, 450, id * 40 + 80))
    U6_sensor_names.append(TextInput(525, id * 40 + 75, 3, 100, 30, "AIN" + str(U6_channel_ids[id])))
    U6_readings_texts.append(Label("No Data", 3, 650, id * 40 + 80))

U6_sensor_labels.append(Label("CJC:", 3, 450, 14 * 40 + 80))
U6_readings_texts.append(Label("No Data", 3, 650, 14 * 40 + 80))

U6_sensor_labels.append(Label("Channel", 2, 450, 50))
U6_sensor_labels.append(Label("Name", 2, 525, 50))
U6_sensor_labels.append(Label("Value", 2, 650, 50))
U6_sensor_labels.append(Label("U6 DAQ", 3, 450, 25))

#Actaul DAQ reading info
T7_Read_Buffer = queue.Queue()
T7_processed_buffer = queue.Queue()
T7_connected = False
T7 = None

U6_Read_Buffer = queue.Queue()
U6_processed_buffer = queue.Queue()
U6_connected = False
U6 = None
U6_CJC = 0
U6_CJC_Updated = False

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
 
# x: standalone command, ECU will process this, no other parameters used
# {x}
# Fire sequence => {20}

#Setting up the valves
for valve_location in valve_locations:
    valve_buttons.append(Button(pnid_center[0] + valve_location[0], pnid_center[1] + valve_location[1],
                                15 if valve_location[2] == 1 else 30, 30 if valve_location[2] == 1 else 15, False,))
    
# for valve_override_location in valve_override_locations:
#     valve_override_buttons.append(Button(pnid_center[0] + valve_override_location[0], pnid_center[1] + valve_override_location[1],
#                                 15 if valve_override_location[2] == 1 else 30, 30 if valve_override_location[2] == 1 else 15, False,
#                                 PINK, GRAY))

def poly_eval(coeffs, x):
    return sum(c * x**i for i, c in enumerate(coeffs))

def type_k_temp_from_voltage(mv):
    """Type K: voltage (mV) → temperature (°C)"""
    if -5.891 <= mv < 0:
        coeffs = [
            0.0000000E+00,
            2.5173462E+01,
            -1.1662878E+00,
            -1.0833638E+00,
            -8.9773540E-01,
            -3.7342377E-01,
            -8.6632643E-02,
            -1.0450598E-02,
            -5.1920577E-04,
        ]
    elif 0 <= mv <= 54.886:
        coeffs = [
            0.000000E+00,
            2.508355E+01,
            7.860106E-02,
            -2.503131E-01,
            8.315270E-02,
            -1.228034E-02,
            9.804036E-04,
            -4.413030E-05,
            1.057734E-06,
            -1.052755E-08,
        ]
    else:
        return -9998
    return poly_eval(coeffs, mv)

def type_t_temp_from_voltage(mv):
    """Type T: voltage (mV) → temperature (°C)"""
    if -5.603 <= mv <= 0:
        coeffs = [
            0.0000000E+00,
            2.5949192E+01,
            -2.1316967E-01,
            7.9018692E-01,
            4.2527777E-01,
            1.3304473E-01,
            2.0241446E-02,
            1.2668171E-03,
        ]
    elif 0 < mv <= 20.872:
        coeffs = [
            0.000000E+00,
            2.592800E+01,
            -7.602961E-01,
            4.637791E-02,
            -2.165394E-03,
            6.048144E-05,
            -7.293422E-07,
        ]
    else:
        return -9998
    return poly_eval(coeffs, mv)

def getCJ(U6):
    return U6.getAIN(14) * -92.6 + 467.6 - 273.15

def getCJMidStream(U6):
    U6.streamStop()
    #print(d.getAIN(14)* -92.6 + 467.6 - 273.15)
    CJ = U6.getAIN(14) * -92.6 + 467.6 - 273.15

    U6.streamStart()

    return CJ

def connect_U6():
    global U6_connected
    global U6

    try:
      U6.streamStop()
      U6.close()
    except:
      pass

    U6 = u6.U6()
    U6.getCalibrationData()
    time.sleep(0.1)

def configure_U6():
   try:
      U6.streamStop()
   except:
      pass
   U6.streamConfig(NumChannels=len(U6_channel_ids), ChannelNumbers=U6_channel_ids, ChannelOptions=[48] * len(U6_channel_ids), SettlingFactor=1, ResolutionIndex=1, ScanFrequency=100)
   #U6.streamConfig(NumChannels=1, ChannelNumbers=[0], ChannelOptions=[48], SettlingFactor=1, ResolutionIndex=1, ScanFrequency=10)
   U6.streamStart()

def read_U6():
   global U6_connected
   global U6_Read_Buffer
   global U6_CJC
   global U6_CJC_Updated

   while True:
      if not U6_connected:
         try:
            connect_U6()
            configure_U6()
            U6_connected = True
         except Exception as e:
            print("U6 Connect", e)
            U6_connected = False
            time.sleep(0.5)
      else:
         try:
            out_data = []
            for r in U6.streamData():
               if r is not None:
                i = 1
                data_is_left = True
                while data_is_left:
                  single_sample = []
                  try:
                    for id in U6_channel_ids:
                      #print(r["AIN" + str(id)])
                      single_sample.append(r["AIN" + str(id)][-i])
                  except:
                     data_is_left = False
                  i += 1

                  if datetime.now().second % 5 == 0 and not CJC_updated:
                    U6_CJC = getCJMidStream(U6)
                    CJC_updated = True
                  elif not datetime.now().second % 5 == 0:
                     CJC_updated = False

                  if len(single_sample) == len(U6_channel_ids):
                    U6_Read_Buffer.put(single_sample + [U6_CJC])
                  
                     
                  #print(single_sample)

            time.sleep(0.01)
         except Exception as e:
            print("READ U6 ERROR:", e)
            U6_connected = False
                #if datetime.now().second % 6 == 0:
                #  CJC_Temp = getCJMidStream(U6)


                #print(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40)#, CJC_Temp + np.mean(r["AIN1"]) * 1e6 / 40, CJC_Temp + np.mean(r["AIN2"]) * 1e6 / 40, CJC_Temp)

                #out = str(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40) + "\n"
                #print(r["AIN14"])
                #s.write(out.encode())

def connect_T7():
  global T7_connected
  global T7

  try:
    if T7 is not None:
      ljm.eStreamStop(T7)
      ljm.close(T7)
  except:
     pass

  T7 = ljm.openS("T7", "USB", "ANY")  # Any device, Any connection, Any identifier
  time.sleep(0.2)
    #info = ljm.getHandleInfo(T7)
    # print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
    #       "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
    #       (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
 # T7_connected = True

def configure_T7():
      global T7_connected

      info = ljm.getHandleInfo(T7)
      numAddresses = len(T7_channel_ids) + 1
      aScanList = ljm.namesToAddresses(numAddresses, T7_channel_ids + ["AIN14"])[0]
      scanRate = 2000
      scansPerRead = scanRate / 2
      # Ensure triggered stream is disabled.
      ljm.eWriteName(T7, "STREAM_TRIGGER_INDEX", 0)
      # Enabling internally-clocked stream.
      ljm.eWriteName(T7, "STREAM_CLOCK_SOURCE", 0)

      aRangeNames = ["AIN0_RANGE", "AIN1_RANGE", "AIN2_RANGE", "AIN3_RANGE", "AIN4_RANGE", "AIN5_RANGE", 
                "AIN6_RANGE", "AIN7_RANGE", "AIN8_RANGE", "AIN9_RANGE", "AIN10_RANGE", "AIN11_RANGE",
                  "AIN12_RANGE", "AIN13_RANGE", "AIN14_RANGE", "STREAM_RESOLUTION_INDEX"]
      
      aRangeValues = []
      for sensor in T7_sensor_types:
         aRangeValues.append(10 if (sensor == "TC_K" or sensor == "TC_T") else 10.0)
      aRangeValues.append(10) #CJC Ain14 range
      aRangeValues.append(0) #Stream resolution index

      #aRangeValues = [1.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 1, 1, 10, 0]

      # Negative channel and settling configurations do not apply to the T8
      if info[0] == ljm.constants.dtT7:
                  #     Negative Channel = 199 (Single-ended)
                  #     Settling = 0 (auto)
        aRangeNames.extend(["AIN0_NEGATIVE_CH", "AIN1_NEGATIVE_CH", "AIN2_NEGATIVE_CH", "AIN3_NEGATIVE_CH", 
                            "AIN4_NEGATIVE_CH", "AIN5_NEGATIVE_CH", "AIN6_NEGATIVE_CH", "AIN7_NEGATIVE_CH", 
                            "AIN8_NEGATIVE_CH", "AIN9_NEGATIVE_CH", "AIN10_NEGATIVE_CH", "AIN11_NEGATIVE_CH", 
                            "AIN12_NEGATIVE_CH", "AIN13_NEGATIVE_CH", "AIN14_NEGATIVE_CH", "STREAM_SETTLING_US"])
        aRangeValues.extend([199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 199, 0])

      numFrames = len(aRangeNames)
      ljm.eWriteNames(T7, numFrames, aRangeNames, aRangeValues)
      scanRate = ljm.eStreamStart(T7, int(scansPerRead), int(numAddresses), aScanList, int(scanRate))

def read_T7():
  global T7_connected
  global T7_Read_Buffer

  while True:
    if not T7_connected:
        try:
          #ljm.eStreamStop(T7)
          #print("Try con")
          connect_T7()
          configure_T7()
          T7_connected = True
          #print("Connected")
        except Exception as e:
          print("CONNECT T7 ERROR", e)
          T7_connected = False
          time.sleep(0.5)

    else:
      try:
        ret = ljm.eStreamRead(T7)
        aData = ret[0]

        n = 15
        #T7_Read_Buffer.put([aData[i::n] for i in range(n)])
        #print([aData])
        #for sample in aData:
           #T7_Read_Buffer.put(sample)
        #print(aData)

        if len(aData) % n == 0:
           broken_up_list = [aData[i:i + n] for i in range(0, len(aData), n)]
           for sample in broken_up_list:
              #print(broken_up_list)
              if len(sample) == 15 and not min(sample) == -9999.0:
                 T7_Read_Buffer.put(sample)
                 #print(sample)

      except Exception as e:
         print("READ T7 ERROR:", e)
         #time.sleep(0.1)
         T7_connected = False

def drawScreen(screen):
    screen.fill(BG_COLOR)  # Clear the screen

    #Valves PNID
    screen.blit(pnid, pnid_rect)
    for button in valve_buttons:
        button.draw(screen)
    for button in valve_override_buttons:
        button.draw(screen)

    #T7
    for label in T7_sensor_labels:
        label.draw(screen, fonts)
    for text in T7_sensor_names:
        text.draw(screen, fonts)
    for text in T7_readings_texts:
        text.draw(screen, fonts)
    
    #U6
    for label in U6_sensor_labels:
        label.draw(screen, fonts)
    for text in U6_sensor_names:
        text.draw(screen, fonts)
    for text in U6_readings_texts:
        text.draw(screen, fonts)


def sigfig_round(x, sig):
    if not x == 0:
      return round(x, sig - int(math.floor(math.log10(abs(x)))) - 1)
    return 0

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

def update_daq_readings(daq_texts, new_data):
    if len(new_data) == 15:
      for i_text in range(len(daq_texts)):
        daq_texts[i_text].text = str(sigfig_round(new_data[i_text], 4))

def proccess_daq(daq="T7"):
  global T7_processed_buffer
  global T7_Read_Buffer
  global U6_processed_buffer
  global U6_Read_Buffer
  
  read_buffer = T7_Read_Buffer if daq=="T7" else U6_Read_Buffer
  sesnor_types = T7_sensor_types if daq=="T7" else U6_sensor_types
  pt_volt_range = T7_pt_voltage_ranges if daq=="T7" else U6_pt_voltage_ranges
  pt_pres_range = T7_pt_pressure_ranges if daq=="T7" else U6_pt_pressure_ranges


  while True:
    try:
      sample = read_buffer.get(timeout=0.01)
      #print(daq, sample)
      # with open(filename_2, 'a', newline='', errors='ignore') as csvfile:
      #       csv_writer = csv.writer(csvfile)
      #       csv_writer.writerow(sample, )

      #print(sample)
      processed_sample = [-9999] * 15

      # # Cold junction approx temp in C
      if daq == "T7":
        processed_sample[14] = sample[14] * -92.6 + 467.6 - 273.15
      else:
         processed_sample[14] = sample[14]

      for i_sensor in range(len(sample)):
        if i_sensor != 14:
          try:
            if sesnor_types[i_sensor] == "TC_K":
              #print((sample[i_sensor]))
              processed_sample[i_sensor] = type_t_temp_from_voltage(sample[i_sensor])*1000 + processed_sample[14]#tc_k_reference.inverse_CmV((sample[i_sensor][-1])*1000, Tref=processed_sample[14])
            elif sesnor_types[i_sensor] == "TC_T":
              processed_sample[i_sensor] = type_t_temp_from_voltage(sample[i_sensor])*1000 + processed_sample[14]#0#tc_t_reference.inverse_CmV((sample[i_sensor][-1])*1000, Tref=processed_sample[14])
            elif sesnor_types[i_sensor] == "PT":
              pmin = pt_pres_range[i_sensor][0]
              pmax = pt_pres_range[i_sensor][1]
              vmin = pt_volt_range[i_sensor][0]
              vmax = pt_volt_range[i_sensor][1]

              processed_sample[i_sensor] = pmin + (sample[i_sensor] - vmin) * (pmax - pmin) / (vmax - vmin)
          except Exception as e:
              print(daq, e)
              processed_sample[i_sensor] = -9999
        if daq == 'T7':
           T7_processed_buffer.put(processed_sample)
        elif daq == 'U6':
           U6_processed_buffer.put(processed_sample)

      # with open(filename, 'a', newline='', errors='ignore') as csvfile:
      #       csv_writer = csv.writer(csvfile)
      #       csv_writer.writerow(processed_sample, )
      #       print(processed_sample  )
    except queue.Empty:
       break
    except Exception as e:
      print("PROC ", daq, e)
      pass #Bad data, we'll ignore


    #T7_processed_buffer.append(processed_sample)
  # if daq == "T7":
  #    T7_Read_Buffer = []
  # elif daq == "U6":
  #    U6_Read_Buffer = []


#Starting daq reads
thread_t7 = threading.Thread(target=read_T7)
thread_t7.start()

thread_u6 = threading.Thread(target=read_U6)
thread_u6.start()

# Main GUI loop
running = True
while running:
    
    #update_daq_readings(T7_readings_texts, [0.0001,1.2154668,2,3,4,5,6,7,8,9,10,11,12,13,14])
    #read_T7()
    # Event handling
    valve_updates = [0] * 14
    valve_override_updates = [0] * 14

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        for i_button in range(len(valve_buttons)):
            valve_updates[valve_index[i_button]] = valve_buttons[valve_index[i_button]].handle_event(event)
            

        for i_button in range(len(valve_override_buttons)):
            valve_override_updates[valve_index[i_button]] += valve_override_buttons[valve_index[i_button]].handle_event(event)

        for sensor in T7_sensor_names:
            sensor.handle_event(event)
        for sensor in U6_sensor_names:
            sensor.handle_event(event)
    
    proccess_daq("T7")
    proccess_daq("U6")

    T7_processed_list = []
    U6_processed_list = []

    while True:
      try:
         #update_daq_readings(T7_readings_texts, )
         T7_processed_list.append(T7_processed_buffer.get(timeout=0.01))
      except queue.Empty:
         break
      
    while True:
      try:
         U6_processed_list.append(U6_processed_buffer.get(timeout=0.01))
         #update_daq_readings(U6_readings_texts, U6_processed_buffer.get(timeout=0.01))
      except queue.Empty:
         break
      
    if len(T7_processed_list) > 0:
       update_daq_readings(T7_readings_texts, T7_processed_list[-1])
    if len(U6_processed_list) > 0:
       update_daq_readings(U6_readings_texts, U6_processed_list[-1])
       #print(U6_CJC)

    # # Processing the incoming commands from RPI
    # while not response_queue.empty():
    #   command = response_queue.get()
    #   print(command)
    #    # -7 => new DAQ data
    #   if command.startswith("{-7,"):
    #       try:
    #          daq_readings = list(map(float, command.strip("{").strip("\n").strip("}").split(",")[1:]))
    #          for i_text in range(len(daq_readings_texts)):
    #             daq_readings_texts[i_text].text = str(daq_readings[i_text])
    #       except:
    #         pass
          

    #   if command.startswith("{1,"):
    #       states = parse_state_string(command)
    #       print("states: ", states, command)
    #       if len(states) == 14:
             
    #         for i,name in enumerate(valve_names):
    #             #valve_name = valve_assign_drops[i].selected
    #             for j, state in enumerate(states):
    #                 if valve_assign_drops[j].selected == name:
    #                   valve_buttons[i].is_on = state == 1
    #                   break
    #                 if j == 13:
    #                     valve_buttons[i].is_on = False
    #             #for j, name in enumerate(valve_names):
    #             #    if name == valve_name:
    #             #        valve_buttons[j].is_on = state == 1

    #         #     index = find_valve_index(valve_names[i])
    #         #     if index > 0 and index < 14:
    #         #         button.is_on[index] = states[i] == 1


    #         #  for i, button in enumerate(valve_buttons):
                
    #         #     button.is_on = states[i] == 1

    # command_buffer = []

    #Drawing screen
    drawScreen(screen)
    # while True:
    #    print(T7_Read_Buffer.get())
    # if len(T7_Read_Buffer) > 0: 
    #   print(T7_Read_Buffer[-1])
    #   T7_Read_Buffer = []
      #time.sleep(1)

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
      pass      
      #command_queue.put("{1," + str(valve_updates.index(1)) + "}")
    if sum(valve_override_updates) > 0:
      pass#command_queue.put("{2," + str(valve_override_updates.index(1)) + "}")

    # Draw updates
    pygame.display.flip()  # Update the display
    clock.tick(60)

# Cleanup
pygame.quit()