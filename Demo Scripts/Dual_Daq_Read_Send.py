import u6
from labjack import ljm
from datetime import datetime
import time
import math
import numpy as np
import traceback
import serial
import sys
import threading

#Conversion functions
def voltToTempTypeK(CJC, volt):
  return CJC + volt * 1e6 / 41

def voltToPressure(volt, max_pressure, min_voltage, max_voltage):
   return (volt - min_voltage) / (max_voltage - min_voltage) * max_pressure

# Global data in buffers
U6_Read_Buffer = []
T7_Read_Buffer = []

# U6 =======================================
# initialize device
d = u6.U6()

# For applying the proper calibration to readings.
d.getCalibrationData()



#CJC functions
def getCJ(d):
    return d.getAIN(14) * -92.6 + 467.6 - 273.15

def getCJMidStream(d):
    d.streamStop()
    
    CJ = d.getAIN(14) * -92.6 + 467.6 - 273.15

    d.streamStart()

    return CJ

d.streamConfig(NumChannels=3, ChannelNumbers=[0, 1, 2], ChannelOptions=[48,48,48], SettlingFactor=1, ResolutionIndex=1, ScanFrequency=100)

CJC_Temp = 20

def readU6():
    global CJC_Temp
    global U6_Read_Buffer

    try:
       d.streamStop()
    except:
       pass
    
    CJC_Temp = d.getAIN(14) * -92.6 + 467.6 - 273.15

    try:
      print("Start stream")
      d.streamStart()
      print("U6 Started")

      for r in d.streamData():
          if r is not None:
              
              if datetime.now().second % 6 == 0:
                CJC_Temp = getCJMidStream(d)

              temp = round(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40, 2)
              #print("U6: " + str(temp) + "C")#, CJC_Temp + np.mean(r["AIN1"]) * 1e6 / 40, CJC_Temp + np.mean(r["AIN2"]) * 1e6 / 40, CJC_Temp)

              U6_Read_Buffer = U6_Read_Buffer + r["AIN0"]
              #U6_Read_Buffer.append(r["AIN0"])

              #out = str(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40) + "\n"
              #s.write(out.encode())

          else:
              print("No data ; %s" % datetime.now())

    except:
        print("".join(i for i in traceback.format_exc()))
    finally:
        d.streamStop()
        print("U6 Stream stopped.\n")
        d.close()


# T7 ======================================

T7 = ljm.openS("T7", "USB", "ANY")  # Any device, Any connection, Any identifier
info = ljm.getHandleInfo(T7)
print("Opened a LabJack with Device type: %i, Connection type: %i,\n"
      "Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" %
      (info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

def readT7():
  global T7_Read_Buffer

  try:
    deviceType = info[0]
    aScanListNames = ["AIN0", "AIN1"]  # Scan list names to stream
    numAddresses = len(aScanListNames)
    aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
    scanRate = 10000
    scansPerRead = int(scanRate / numAddresses)

    # Ensure triggered stream is disabled.
    ljm.eWriteName(T7, "STREAM_TRIGGER_INDEX", 0)
    # Enabling internally-clocked stream.
    ljm.eWriteName(T7, "STREAM_CLOCK_SOURCE", 0)

    aNames = ["AIN0_RANGE", "AIN1_RANGE", "STREAM_RESOLUTION_INDEX"]
    aValues = [10.0, 10.0, 0]


    # Negative channel and settling configurations do not apply to the T8
    if deviceType == ljm.constants.dtT7:
                #     Negative Channel = 199 (Single-ended)
                #     Settling = 0 (auto)
      aNames.extend(["AIN0_NEGATIVE_CH", "STREAM_SETTLING_US",
                              "AIN1_NEGATIVE_CH"])
      aValues.extend([199, 0, 199])

    numFrames = len(aNames)
    ljm.eWriteNames(T7, numFrames, aNames, aValues)

    # Configure and start stream
    scanRate = ljm.eStreamStart(T7, scansPerRead, numAddresses, aScanList, scanRate)
    print("\n T7 Stream started with a scan rate of %0.0f Hz." % scanRate)

    i = 1
    while True:
      ret = ljm.eStreamRead(T7)
      aData = ret[0]

      T7_Read_Buffer = T7_Read_Buffer + aData[::2]
      


  except:
    e = sys.exc_info()[1]
    print(e)
  finally:
    try:
      print("\n T7 Stop Stream")
      ljm.eStreamStop(T7)
    except Exception:
      e = sys.exc_info()[1]
      print(e)

    ljm.close(T7)

s = serial.Serial("/dev/ttyACM0", 115200, timeout=1)

def readData():
  global U6_Read_Buffer
  global T7_Read_Buffer
  global CJC_Temp

  while True:

    #print(U6_Read_Buffer)

    #round(voltToPressure(np.mean(T7_Read_Buffer), 1000, 0.5, 4.5)
    out = "U6: " + str(round(voltToTempTypeK(CJC_Temp, np.mean(U6_Read_Buffer)), 2)) + " | " + str(len(U6_Read_Buffer)) +  "  T7: " + str(round(voltToPressure(np.mean(T7_Read_Buffer), 1000, 0.5, 4.5), 2)) + " | " + str(len(T7_Read_Buffer)) + "\n"
    print(out)
    #print("U6:", round(voltToTempTypeK(CJC_Temp, np.mean(U6_Read_Buffer)), 2), len(U6_Read_Buffer), "T7", round(voltToPressure(np.mean(T7_Read_Buffer), 1000, 0.5, 4.5), 2), len(T7_Read_Buffer))
    #print("U6:", round(voltToTempTypeK(CJC_Temp, np.mean(U6_Read_Buffer)), 2), len(U6_Read_Buffer), "T7", round(np.mean(T7_Read_Buffer), 2), len(T7_Read_Buffer))
    #print()

    s.write(out.encode())

    U6_Read_Buffer = []
    T7_Read_Buffer = []

    time.sleep(1)

#readU6()
#readT7()

thread_u6 = threading.Thread(target=readU6)
thread_t7 = threading.Thread(target=readT7)
thread_read = threading.Thread(target=readData)

thread_u6.start()
thread_t7.start()
thread_read.start()

thread_u6.join()
thread_t7.join()
thread_read.join()