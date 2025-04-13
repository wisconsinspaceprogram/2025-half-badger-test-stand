import csv
import math
import os
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

from thermocouples_reference import thermocouples
tc_t_reference = thermocouples['T']

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
valve_override_locations = [(-135, -250, 1), (-30, -280, 0), (-120, 170, 0), (-70, 340, 0), (70, -80, 0), (-90, -290, 0), (-50, 90, 0), (150, 80, 0), (170, 45, 0), (-160, -20, 0), (-210, -70, 0), (40, 250, 0), (175, 200, 0)]
valve_override_buttons = []

# Making the pyro channel manual override buttons and such
pyro_center = (1100, 750)
pyro_labels = [Label("Pyro 1: ", 3, pyro_center[0], pyro_center[1]), Label("Pyro 2: ", 3, pyro_center[0], pyro_center[1]+30)]
pyro_buttons = [Button(pyro_center[0] + 65, pyro_center[1], 30, 15, False), Button(pyro_center[0]+ 65, pyro_center[1]+30, 30, 15, False)]
pyro_override_buttons = [Button(pyro_center[0]+100, pyro_center[1], 30, 15, False, PINK, GRAY), Button(pyro_center[0]+100, pyro_center[1]+30, 30, 15, False, PINK, GRAY)]
                                

# Sensor Update Shit
T7_channel_ids = ["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AIN10", "AIN11", "AIN12", "AIN13"]
T7_sensor_types = ["PT", "PT", "PT", "PT", "PT", "PT", "PT", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "LOAD"]
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
U6_sensor_types = ["TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T", "TC_T"]
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

# Other useful info
stateText = Label("State: ", 3, 50, 700)
batteryText = Label("Battery: ??.??V", 3, 50, 740)
lastCommandRecieved = Label("Last Command: ??s", 3, 50, 780)
lastStateChange = Label("Last State: ??s", 3, 50, 820)
loadSequenceLabel = Label("Load Sequence From File: ", 3, 50, 860)
loadSequenceButton = Button(270, 860, 30, 15, False, BLUE, BLUE)

startSequenceLabel = Label("Start Sequence: ", 3, 850, 860)
startSequenceButon = Button(800, 860, 30, 15, False, BLUE, BLUE)

highResDataButton = Button(800, 830, 30, 15, True, GREEN, GRAY)
highResDataLabel = Label("Log Full Res T7: ", 3, 850, 830)

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

# ECU Info
ecu_command_buffer = queue.Queue()
ecu_serial = None
ecu_port = "COM15"
ecu_baud = 115200
ecu_connected = False

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
 
# 3, 4, same as 1, 2 but for pyro channels 1 and 2, index 0 and 1

# x: standalone command, ECU will process this, no other parameters used
# {x}
# Fire sequence => {20}

#Setting up the valves
for valve_location in valve_locations:
    valve_buttons.append(Button(pnid_center[0] + valve_location[0], pnid_center[1] + valve_location[1],
                                15 if valve_location[2] == 1 else 30, 30 if valve_location[2] == 1 else 15, False,))
    
for valve_override_location in valve_override_locations:
    valve_override_buttons.append(Button(pnid_center[0] + valve_override_location[0], pnid_center[1] + valve_override_location[1],
                                15 if valve_override_location[2] == 1 else 30, 30 if valve_override_location[2] == 1 else 15, False,
                                PINK, GRAY))

def poly_eval(coeffs, x):
    return sum(c * x**i for i, c in enumerate(coeffs))

def type_k_temp_from_voltage(mv):
    """Type K: voltage (mV) → temperature (°C)"""
    #if -5.891 <= mv < 0:
    if mv < 0:
        coeffs = [
            0.0000000E+00,
            2.5173462E+01,
            -1.1662878E-03,
            -1.0833638E-6,
            -8.9773540E-10,
            -3.7342377E-13,
            -8.6632643E-17,
            -1.0450598E-20,
            -5.1920577E-25,
        ]
    #elif 0 <= mv <= 54.886:
    elif mv >= mv:
        coeffs = [
            0.000000E+00,
            2.508355E+01,
            7.860106E-05,
            -2.503131E-7,
            8.315270E-11,
            -1.228034E-14,
            9.804036E-19,
            -4.413030E-23,
            1.057734E-27,
            -1.052755E-32,
        ]
    else:
        return -9998
    return poly_eval(coeffs, mv)

def type_t_temp_from_voltage(mv):
    """Type T: voltage (mV) → temperature (°C)"""
    #if -5.603 <= mv <= 0:
    if mv <= 0:
        coeffs = [
            0.0000000E+00,
            2.5949192E+01,
            -2.1316967E-04,
            7.9018692E-07,
            4.2527777E-10,
            1.3304473E-13,
            2.0241446E-17,
            1.2668171E-21,
        ]
    #elif 0 < mv <= 20.872:
    elif 0 < mv:
        coeffs = [
            0.000000E+00,
            2.592800E+01,
            -7.602961E-04,
            4.637791E-8,
            -2.165394E-12,
            6.048144E-17,
            -7.293422E-22,
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
      scanRate = 500
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

    #Extra info
    stateText.draw(screen, fonts)
    batteryText.draw(screen, fonts)
    lastCommandRecieved.draw(screen, fonts)
    lastStateChange.draw(screen, fonts)
    loadSequenceLabel.draw(screen, fonts)
    loadSequenceButton.draw(screen)
    startSequenceButon.draw(screen)
    startSequenceLabel.draw(screen, fonts)
    highResDataButton.draw(screen)
    highResDataLabel.draw(screen, fonts)

    for item in pyro_labels:
       item.draw(screen, fonts)
    for item in pyro_buttons:
       item.draw(screen)
    for item in pyro_override_buttons:
       item.draw(screen)


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
              processed_sample[i_sensor] = type_k_temp_from_voltage(sample[i_sensor]*1000) + processed_sample[14]#tc_k_reference.inverse_CmV((sample[i_sensor][-1])*1000, Tref=processed_sample[14])
            elif sesnor_types[i_sensor] == "TC_T":
              processed_sample[i_sensor] = type_t_temp_from_voltage(sample[i_sensor]*1000) + processed_sample[14] #tc_t_reference.inverse_CmV((sample[i_sensor])*1000, Tref=processed_sample[14])# sample[i_sensor]*1000#type_t_temp_from_voltage(sample[i_sensor])*1000 + processed_sample[14]#0#tc_t_reference.inverse_CmV((sample[i_sensor][-1])*1000, Tref=processed_sample[14])
              #print("t")
            elif sesnor_types[i_sensor] == "PT":
              pmin = pt_pres_range[i_sensor][0]
              pmax = pt_pres_range[i_sensor][1]
              vmin = pt_volt_range[i_sensor][0]
              vmax = pt_volt_range[i_sensor][1]

              processed_sample[i_sensor] = pmin + (sample[i_sensor] - vmin) * (pmax - pmin) / (vmax - vmin)
            elif sesnor_types[i_sensor] == "LOAD":
               processed_sample[i_sensor] = sample[i_sensor]
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

def read_command_ecu():
    global ecu_connected
    try:
      buffer = ""
      while True:
        if ecu_serial.in_waiting > 0:
            data = ecu_serial.readline(ecu_serial.in_waiting).decode('utf-8', errors='ignore')
            
            if data == "{":
                buffer = ""

            buffer += data
            while '{' in buffer and '}' in buffer:
                start = buffer.find('{')
                end = buffer.find('}', start)
                if end != -1 and end > start:
                    command = buffer[start:end+1]  # Include the {} in the command
                    buffer = buffer[end+1:]
                    ecu_command_buffer.put(command)
                    print(command)
                else:
                   break
        else:
           time.sleep(0.01)
    except:
       ecu_connected = False

def start_reading_ecu():
    global ecu_connected
    try:
        thread = threading.Thread(target=read_command_ecu, args=(), daemon=True)
        thread.start()
    except serial.SerialException as e:
        ecu_connected = False

#Starting daq reads
thread_t7 = threading.Thread(target=read_T7)
thread_t7.start()

thread_u6 = threading.Thread(target=read_U6)
thread_u6.start()

filename_t7 = os.path.dirname(__file__)+'/Logs/' + str(datetime.now()).replace(" ", "_").replace(".", "_").replace(":", "_") + '_t7.csv'
filename_t7_high_res = os.path.dirname(__file__)+'/Logs/' + str(datetime.now()).replace(" ", "_").replace(".", "_").replace(":", "_") + '_t7_detailed.csv'
filename_u6 = os.path.dirname(__file__)+'/Logs/' + str(datetime.now()).replace(" ", "_").replace(".", "_").replace(":", "_") + '_u6.csv'
filename_ecu_tx = os.path.dirname(__file__)+'/Logs/' + str(datetime.now()).replace(" ", "_").replace(".", "_").replace(":", "_") + '_ecu_tx.csv'
filename_ecu_rx = os.path.dirname(__file__)+'/Logs/' + str(datetime.now()).replace(" ", "_").replace(".", "_").replace(":", "_") + '_ecu_rx.csv'

def log_ecu_tx(command):
   try:
    with open(filename_ecu_tx, 'a', newline='', errors='ignore') as csvfile:
              csv_writer = csv.writer(csvfile)
              #for sample in T7_processed_list:
              csv_writer.writerow([datetime.now(), command], )
   except Exception as e:
      print(e)

# Main GUI loop
running = True
while running:
    
    if not ecu_connected or ecu_serial == None:
      try:
          ecu_serial = serial.Serial(ecu_port, ecu_baud, timeout=2)
          #ecu_serial.setDTR(False)
          ecu_connected = True
          start_reading_ecu()
      except:
          ecu_connected = False

    #update_daq_readings(T7_readings_texts, [0.0001,1.2154668,2,3,4,5,6,7,8,9,10,11,12,13,14])
    #read_T7()
    # Event handling
    valve_updates = [0] * 14
    valve_override_updates = [0] * 14

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Valve updates
        for i_button in range(len(valve_buttons)):
            #valve_updates[valve_index[i_button]] = valve_buttons[valve_index[i_button]].handle_event(event)
            if valve_buttons[valve_index[i_button]].handle_event(event) == 1:
              try:
                 ecu_serial.write(("{1," + str(valve_index[i_button]) + "}").encode())
                 log_ecu_tx("{1," + str(valve_index[i_button]) + "}")
              except Exception as e:
                 print(e)
              #print(("{1," + str(valve_index[i_button]) + "}").encode())
        for i_button in range(len(valve_override_buttons)):
            if valve_override_buttons[valve_index[i_button]].handle_event(event) == 1:
              try:
                  ecu_serial.write(("{2," + str(valve_index[i_button]) + "}").encode())
                  log_ecu_tx("{2," + str(valve_index[i_button]) + "}")
              except Exception as e:
                 print(e)
            #valve_override_updates[valve_index[i_button]] += valve_override_buttons[valve_index[i_button]].handle_event(event)

        #Pyro Updates
        for i_button in range(len(pyro_buttons)):
            if pyro_buttons[i_button].handle_event(event) == 1:
              ecu_serial.write(("{3," + str(i_button) + "}").encode())
              log_ecu_tx("{3," + str(i_button) + "}")
        for i_button in range(len(pyro_override_buttons)):
            if pyro_override_buttons[i_button].handle_event(event) == 1:
              ecu_serial.write(("{4," + str(i_button) + "}").encode())
              log_ecu_tx("{4," + str(i_button) + "}")

        if loadSequenceButton.handle_event(event) == 1:
           open_path = easygui.fileopenbox("State Data to open")
           
           if open_path != None:
              with open(open_path, "rb") as file:
                loaded_data = dill.load(file)

                state_numbers = loaded_data["numbers"]
                state_operations = loaded_data["operations"]
                state_ids = loaded_data['ids']
                state_thresholds = loaded_data['thresholds']
                state_num_sensors = loaded_data['num_sensors']
                state_physical_state = loaded_data['physical']
                state_to_states = loaded_data['toNumbers']

                # Bro fuck this function
                for i in range(len(state_numbers)):
                   print(state_to_states[i])
                   #print(state_numbers[i], state_operations[i][0], state_ids[i][0], state_thresholds[i][0], state_num_sensors[i][0], state_physical_state[i])

                   outString = "{9,"

                   outString += str(int(state_numbers[i]))
                   outString += ","

                   opString = ""
                   for op in range(3):
                      opString += "0" if state_operations[i][0][op] == '<' else ("1" if state_operations[i][0][op] == '=' else "2")
                      opString += ","

                   outString += opString

                   state_id_string = ""
                   for id in range(3):
                      state_id_string += "101" if state_ids[i][0][id] == 'T_STATE' else ("103" if state_ids[i][0][id] == "COMMAND" else "0")
                      state_id_string += ","

                   outString += state_id_string

                   thresh_string = ""
                   for thresh in range(3):
                      thresh_string += state_thresholds[i][0][thresh]
                      if len(state_thresholds[i][0][thresh]) == 0:
                         thresh_string += "0"
                      thresh_string += ","
                    
                   outString += thresh_string

                   physical_state_string = ""
                   for j in range(14):
                      index = -1
                      try:
                         index = valve_index.index(j)
                      except:
                        pass
                      
                      if index == -1:
                         physical_state_string += "0,"
                      else:
                         #print(valve_names[index])
                         #print(state_physical_state[i])
                         physical_state_string += str(state_physical_state[i][valve_names[index]])
                         physical_state_string += ","
                 
                   physical_state_string += str(state_physical_state[i]['PYRO1'])
                   physical_state_string += ","
                   physical_state_string += str(state_physical_state[i]['PYRO2'])
                   physical_state_string += ","


                   toStateString = ""
                   for j in range(3):
                      toStateString += state_to_states[i][0][j]
                      if len(state_to_states[i][0][j]) == 0:
                         toStateString += '0'
                      toStateString += ','
                  
                   outString += toStateString

                   outString += physical_state_string
                   outString = outString[:-1] + '}' 

                   try:
                      ecu_serial.write(outString.encode())
                   except Exception as e:
                      print(e)
                    
                   time.sleep(0.1)
                   #print(outString)

        if startSequenceButon.handle_event(event) == 1:
           if ecu_connected:
              ecu_serial.write(("{15}").encode())
              log_ecu_tx("{15}")

        highResDataButton.handle_event(event)

        for sensor in T7_sensor_names:
            sensor.handle_event(event)
        for sensor in U6_sensor_names:
            sensor.handle_event(event)
    
    proccess_daq("T7")
    proccess_daq("U6")

    T7_processed_list = []
    U6_processed_list = []
    #print(ecu_command_buffer.qsize())
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
       with open(filename_t7, 'a', newline='', errors='ignore') as csvfile:
            csv_writer = csv.writer(csvfile)
            #for sample in T7_processed_list:
            csv_writer.writerow([datetime.now()] + T7_processed_list[-1], )

    if len(T7_processed_list) > 0 and highResDataButton.is_on:
       t = datetime.now().strftime("%H:%M:%S")
       processed_rows = []

       for row in T7_processed_list:
          processed = [sigfig_round(val, 4) for val in row]
          processed_rows.append([t, processed[0], processed[1], processed[2], processed[3], processed[4]])
       
       with open(filename_t7_high_res, 'a', newline='', errors='ignore') as csvfile:
            csv_writer = csv.writer(csvfile)
            csv_writer.writerows(processed_rows)
            
            #for sample in T7_processed_list:
            #  csv_writer.writerow([t] + sample, )
    
    if len(U6_processed_list) > 0:
       with open(filename_u6, 'a', newline='', errors='ignore') as csvfile:
            csv_writer = csv.writer(csvfile)
            #for sample in U6_processed_list:
            csv_writer.writerow([datetime.now()] + U6_processed_list[-1], )
      
    if len(T7_processed_list) > 0:
       update_daq_readings(T7_readings_texts, T7_processed_list[-1])
    if len(U6_processed_list) > 0:
       update_daq_readings(U6_readings_texts, U6_processed_list[-1])
       #print(U6_CJC)

    while True:
      try:
        ecu_command = ecu_command_buffer.get(timeout=0.01)
          
        if ecu_command.startswith("{1,"):
            states = parse_state_string(ecu_command)
            
            if len(states) == 14:
              #print("states: ", states, ecu_command)

              for i, state in enumerate(states):
                if i in valve_index:
                   valve_buttons[valve_index.index(i)].is_on = state == 1

        if ecu_command.startswith("{2,"):
            states = parse_state_string(ecu_command)
            
            if len(states) == 14:
              #print("states: ", states, ecu_command)

              for i, state in enumerate(states):
                if i in valve_index:
                   valve_override_buttons[valve_index.index(i)].is_on = state == 1

        if ecu_command.startswith("{3,"):
            states = parse_state_string(ecu_command)
            if len(states) == 4:
               pyro_buttons[0].is_on = states[0]
               pyro_buttons[1].is_on = states[1]
               pyro_override_buttons[0].is_on = states[2]
               pyro_override_buttons[1].is_on = states[3]

        if ecu_command.startswith("{9,"):
           batteryText.text = "Battery: " + ecu_command[3:-1] + "V"
        if ecu_command.startswith("{8,"):
           stateText.text = "State: " + ecu_command[3:-1]
        if ecu_command.startswith("{7,"):
           lastCommandRecieved.text = "Last Command: " + ecu_command[3:-1] + "s"
        if ecu_command.startswith("{6,"):
           lastStateChange.text = "Last State: " + ecu_command[3:-1] + "s"

        with open(filename_ecu_rx, 'a', newline='', errors='ignore') as csvfile:
            csv_writer = csv.writer(csvfile)
            #for sample in T7_processed_list:
            csv_writer.writerow([datetime.now(), ecu_command], )
      except queue.Empty:
         break
      
    #Drawing screen
    drawScreen(screen)

    # Draw updates
    pygame.display.flip()  # Update the display
    clock.tick(60)

# Cleanup
pygame.quit()