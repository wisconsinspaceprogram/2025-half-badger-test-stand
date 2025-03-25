import serial

# Setup serial connection
ser = serial.Serial(
    port='COM6',        # Replace with your COM port
    baudrate=115200,
    timeout=1           # Read timeout in seconds
)

try:
    while True:
        if ser.in_waiting:             # Check if there's data to read
            data = ser.readline()      # Read data
            print(data.decode('utf-8').strip())  # Print data as a string
except KeyboardInterrupt:
    print("Interrupted by user")

finally:
    ser.close()   # Ensure the serial connection is closed when done
