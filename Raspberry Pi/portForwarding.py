import math
import re
import serial
import threading
import time
from labjack import ljm
from thermocouples_reference import thermocouples
from statistics import mean
from datetime import datetime


# RPI Command list, these commands are not passed to the ECU if detected, only valid codes for the ECU are transmitted
# Update names:
# {-1,NAME1,NAME2,NAME3,NAME4...NAME14}

# Update sensor type: P => PT, T => Type T TC, K => Type K TC
# {-2,K,T,K,K,K,P,P...}

# Update pt pressure ranges, 14x
# {-3, (0,100), (0,1500),...}

# Update PT voltage ranges, 14x
# {-4, (1,4), (1,10), (0,10)...}

# Dump saved datafile - not needed yet but would be nice eventually, can retrive data from ethernet
# {-5}

radio_port = "COM6"
ecu_port = "COM7"

radio_baud = 115200
ecu_baud = 115200

ecu_serial = None
radio_serial = None

# last_radio_rx = 0
# lastFrameTime = 0

radio_connected = False
ecu_connected = False

daq_channel_ids = ["AIN0", "AIN1", "AIN2", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AIN10", "AIN11", "AIN12", "AIN13"]
daq_names = ["LOX_TC", "GOOFY_PT", "BOOM_DETECTOR", "AIN3", "AIN4", "AIN5", "AIN6", "AIN7", "AIN8", "AIN9", "AIN10", "AIN11", "AIN12", "AIN13"]
daq_sensor_types = ["PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "PT", "TC_K", "TC_K"]
daq_pt_pressure_ranges = [(0, 1500)] * 14
daq_pt_voltage_ranges = [(0, 10)] * 14

#TC refernce 
tc_k_reference = thermocouples['K']
tc_t_reference = thermocouples['T']

# Incoming command buffer full of only commands that are enclosed by {}
command_buffer = []
ecu_command_buffer = []
radio_out_buffer = []

# Buffers for the DAQ readings
T7_Read_Buffer = []
T7_processed_buffer = []
T7_connected = False
T7 = None

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
  time.sleep(0.1)
    #info = ljm.getHandleInfo(T7)
    # print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
    #       "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
    #       (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))
  T7_connected = True

def configure_T7():
      global T7_connected

      info = ljm.getHandleInfo(T7)
      numAddresses = len(daq_channel_ids) + 1
      aScanList = ljm.namesToAddresses(numAddresses, daq_channel_ids + ["AIN14"])[0]
      scanRate = 100
      scansPerRead = scanRate * 2 # Return stream data every 0.5s
      # Ensure triggered stream is disabled.
      ljm.eWriteName(T7, "STREAM_TRIGGER_INDEX", 0)
      # Enabling internally-clocked stream.
      ljm.eWriteName(T7, "STREAM_CLOCK_SOURCE", 0)

      aRangeNames = ["AIN0_RANGE", "AIN1_RANGE", "AIN2_RANGE", "AIN3_RANGE", "AIN4_RANGE", "AIN5_RANGE", 
                "AIN6_RANGE", "AIN7_RANGE", "AIN8_RANGE", "AIN9_RANGE", "AIN10_RANGE", "AIN11_RANGE",
                  "AIN12_RANGE", "AIN13_RANGE", "AIN14_RANGE", "STREAM_RESOLUTION_INDEX"]
      
      aRangeValues = []
      for sensor in daq_sensor_types:
         aRangeValues.append(1 if (sensor == "TC_K" or sensor == "TC_T") else 10.0)
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
          #print("True")
        except Exception as e:
          print(e)
          #T7_connected = False
          time.sleep(0.5)

    else:
      try:
        ret = ljm.eStreamRead(T7)
        aData = ret[0]

        n = 15
        T7_Read_Buffer.append([aData[i::n] for i in range(n)])
        #print([aData[i::n] for i in range(n)])
      except Exception as e:
         print(e)
         time.sleep(0.1)
         T7_connected = False
    
def proccess_daq():
  global T7_processed_buffer
  global T7_Read_Buffer


  for i_sample in range(len(T7_Read_Buffer)):
    try:
      sample = T7_Read_Buffer[i_sample]
      #print(sample)
      processed_sample = [-9999] * 15

      # Cold junction approx temp in C
      processed_sample[14] = mean(sample[14]) * -92.6 + 467.6 - 273.15

      for i_sensor in range(len(sample)):
        if i_sensor != 14:
          try:
            if daq_sensor_types[i_sensor] == "TC_K":
              #print((sample[i_sensor]))
              processed_sample[i_sensor] = tc_k_reference.inverse_CmV(mean(sample[i_sensor])*1000, Tref=processed_sample[14])
            elif daq_sensor_types[i_sensor] == "TC_T":
              processed_sample[i_sensor] = tc_t_reference.inverse_CmV(mean(sample[i_sensor])*1000, Tref=processed_sample[14])
            elif daq_sensor_types[i_sensor] == "PT":
              pmin = daq_pt_pressure_ranges[i_sensor][0]
              pmax = daq_pt_pressure_ranges[i_sensor][1]
              vmin = daq_pt_voltage_ranges[i_sensor][0]
              vmax = daq_pt_voltage_ranges[i_sensor][1]

              processed_sample[i_sensor] = pmin + (mean(sample[i_sensor]) - vmin) * (pmax - pmin) / (vmax - vmin)
          except Exception as e:
              print(e)
              processed_sample[i_sensor] = -9999
    except Exception as e:
      print(e)
      pass #Bad data, we'll ignore
    T7_processed_buffer.append(processed_sample)
  T7_Read_Buffer = []

# def seconds_since_midnight():
#     # Get the current time
#     now = datetime.now()
    
#     # Calculate the seconds since midnight (00:00)
#     midnight = datetime.combine(now.date(), datetime.min.time())
#     delta = now - midnight
#     return delta.total_seconds()

# Function to read the command including the {} characters
command_threshold = 1

def read_command(ser):
    # global last_radio_rx
    # global command_threshold

    buffer = ""
    while True:
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
                  # if command.startswith("{0,"):
                  #    try:
                  #     command_threshold = command[3]
                  #    except:
                  #       command_threshold = 1
                  # else:
                  command_buffer.append(command)
                  # last_radio_rx = seconds_since_midnight()
                  #print("NEW_COMMAND")command_buffer)
                  break
              
def read_command_ecu():
    buffer = ""
    while True:
      if ecu_serial.in_waiting > 0:
          data = ecu_serial.read(ecu_serial.in_waiting).decode('utf-8', errors='ignore')
          
          if data == "{":
              buffer = ""

          buffer += data
          while '{' in buffer and '}' in buffer:
              start = buffer.find('{')
              end = buffer.find('}', start)
              if end != -1 and end > start:
                  command = buffer[start:end+1]  # Include the {} in the command
                  buffer = buffer[end+1:]
                  ecu_command_buffer.append(command)
                  break

# Function to start the reading process in a background thread
def start_reading_radio():
    global radio_connected
    try:
        thread = threading.Thread(target=read_command, args=(radio_serial,), daemon=True)
        thread.start()
    except serial.SerialException as e:
        radio_connected = False

def start_reading_ecu():
    global ecu_connected
    try:
        thread = threading.Thread(target=read_command_ecu, args=(), daemon=True)
        thread.start()
    except serial.SerialException as e:
        ecu_connected = False

def radio_send(command):
    global radio_connected
    #print(command)
    if radio_connected:
      # cur_time = seconds_since_midnight()
      # start_wait_time = cur_time
      # last_send_time = last_radio_rx

      # while ((cur_time - last_send_time) < 0.2 and (cur_time - start_wait_time) < 2):
      #    print("WAITING")
      #    cur_time = seconds_since_midnight()
      #    time.sleep(0.01)

      try:
        #print(command)
        # print(command)
        radio_serial.write(command.encode())
      except:
        radio_connected = False   
        
def extract_strings(input_str):
    items = input_str.strip('{}').split(',')  # remove both { and } and split
    return items[1:]  # skip the first item (like -1)

def extract_tuples(input_str):
    matches = re.findall(r'\(([^)]+)\)', input_str)  # find content inside each pair of parentheses
    tuples = [tuple(map(int, m.split(','))) for m in matches]  # split and convert to int
    return tuples

# Main run loop
if __name__ == "__main__":
    # Setting up continous daq readings - read_T7() will reconnect if the DAQ has disconnected
    thread_t7 = threading.Thread(target=read_T7)
    thread_t7.start()

    while True:
        
        # Starting the reading of the radio, trying to reconnect if disconnected
        if not radio_connected or radio_serial == None:
          try:
            radio_serial = serial.Serial(radio_port, radio_baud, timeout=2)
            radio_connected = True
            start_reading_radio()
          except:
            radio_connected = False

        if not ecu_connected or ecu_serial == None:
            try:
                ecu_serial = serial.Serial(ecu_port, ecu_baud, timeout=2)
                ecu_connected = True
                start_reading_ecu()
            except:
                ecu_connected = False
        #print(daq_pt_pressure_ranges, len(command_buffer), command_threshold)
        # Processing the command
        if len(command_buffer) > 0:
          for command in command_buffer:
              try:
                #print("InCOMING:", command)
                if command[1:2] == "-":
                    #RPI Command
                    if command.startswith("{-1,"):
                      daq_names = extract_strings(command)
                    elif command.startswith("{-2,"):
                      daq_sensor_types = extract_strings(command)
                    elif command.startswith("{-3"):
                      try:
                        daq_pt_pressure_ranges_raw = extract_tuples(command)
                        if len(daq_pt_pressure_ranges_raw) == 14:
                            daq_pt_pressure_ranges = daq_pt_pressure_ranges_raw
                      except:
                        pass
                    elif command.startswith("{-4"):
                      try:
                        daq_pt_voltage_ranges_raw = extract_tuples(command)
                        if len(daq_pt_voltage_ranges_raw) == 14:
                            daq_pt_voltage_ranges = daq_pt_voltage_ranges_raw
                      except:
                        pass
                    elif command.startswith("{-5"):
                        sent_commands = []
                        #time.sleep(0.5)
                        for s in range(len(radio_out_buffer)-1,-1,-1):
                          if not (radio_out_buffer[s][1:3] in sent_commands):
                            radio_send(radio_out_buffer[s])
                            sent_commands.append(radio_out_buffer[s][1:3])

                    #print(command)
                    pass
                elif command[1:2].isdigit():
                    #ECU Command
                    print("Send to ECU: " + command)
                    ecu_serial.write(command.encode('utf-8'))
                    pass
              except:
                 pass
          command_buffer = []
        
        # if ecu_serial != None:
        #   if ecu_serial.in_waiting > 0:
        #     print(ecu_serial.read(ecu_serial.in_waiting).decode('utf-8', errors='ignore'))

        #Make the call to process the data into the buffer
        proccess_daq()
        
        for sample in T7_processed_buffer:
           radio_out_buffer.append("{-7," + ",".join(map(str, sample)) + "}")
           #print("{-7," + ",".join(map(str, sample)) + "}")

        for ecu_command in ecu_command_buffer:
           radio_out_buffer.append(ecu_command)
        
        # frameTime = seconds_since_midnight()
        # if (math.floor(frameTime) - math.floor(lastFrameTime)) > 0:
        #     for out in radio_out_buffer:
        #       radio_send(out)

            # radio_out_buffer = []
        # lastFrameTime = frameTime

        if len(radio_out_buffer) > 100:
           radio_out_buffer.pop(0)

        ecu_command_buffer = []
        T7_processed_buffer = []

        #print(T7_connected)
        time.sleep(0.1)


# read any incoming commands
# process command if for rpi
  # - Set logging rate
  # - Update DAQ wiring configs
  # - Request data
# if not for rpi write command to ECU
# read data from DAQ if ready
  # Process daq data
  # save to file
# write averaged data to ECU