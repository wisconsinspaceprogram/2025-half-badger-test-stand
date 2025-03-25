import serial
import datetime
import time

s = serial.Serial("COM6", 115200, timeout=1)

i = 0

while True:
  out = str(i) + "\n"
  s.write(out.encode())

  i += 1

  time.sleep(1)