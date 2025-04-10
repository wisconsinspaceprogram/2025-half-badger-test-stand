import u6
from datetime import datetime
import time
import math
import numpy as np
import traceback
import serial

#s = u6.U6(firstFound=True, localId=None, serial=None)#serial.Serial('LabJack U6', baudrate=115200, timeout=1)

d = u6.U6()

# For applying the proper calibration to readings.
d.getCalibrationData()

def getCJ(d):
    return d.getAIN(14) * -92.6 + 467.6 - 273.15

def getCJMidStream(d):
    d.streamStop()
    print(d.getAIN(14)* -92.6 + 467.6 - 273.15)
    CJ = d.getAIN(14) * -92.6 + 467.6 - 273.15

    d.streamStart()

    return CJ

print("Configuring U6 stream")

d.streamConfig(NumChannels=1, ChannelNumbers=[0], ChannelOptions=[48], SettlingFactor=1, ResolutionIndex=1, ScanFrequency=10000)


CJC_Temp = d.getAIN(14) * -92.6 + 467.6 - 273.15

try:
    print("Start stream")
    d.streamStart()
    start = datetime.now()
    print("Start time is %s" % start)

    missed = 0
    dataCount = 0
    packetCount = 0

    for r in d.streamData():
        if r is not None:
            
            if datetime.now().second % 6 == 0:
              CJC_Temp = getCJMidStream(d)


            #print(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40)#, CJC_Temp + np.mean(r["AIN1"]) * 1e6 / 40, CJC_Temp + np.mean(r["AIN2"]) * 1e6 / 40, CJC_Temp)

            #out = str(CJC_Temp + np.mean(r["AIN0"]) * 1e6 / 40) + "\n"
            #print(r["AIN14"])
            #s.write(out.encode())

        else:
            print("No data ; %s" % datetime.now())
except:
    print("".join(i for i in traceback.format_exc()))
finally:
    d.streamStop()
    print("Stream stopped.\n")
    d.close()
