from datetime import datetime
import math
from pathlib import Path
import random
from labjack import ljm
import time
from statistics import mean
import threading
from thermocouples_reference import thermocouples
import traceback
from core import utils

tc_T = thermocouples["T"]
tc_K = thermocouples["K"]

SERIAL_NUMBER = 470012365

# Variables for the T7
daq_channel_numbers = [1, 2]
daq_sensor_types = ["Pressure Transducer", "Thermocouple Type K"]
daq_sensor_locations = ["Combustion Chamber", "IPA Tank Top"]
daq_mappings = [((0, 10), (0, 100)), ((0, 10), (0, 1000))]
scan_rate = 20

cur_stream_daq_sensor_types = daq_sensor_types
cur_stream_daq_sensor_numbers = daq_channel_numbers
cur_stream_daq_sensor_locations = daq_sensor_locations
cur_stream_daq_mappings = daq_mappings
cur_stream_scan_rate = scan_rate

T7_connected = False
T7 = None
unixStartTime = time.time()

processed_buffer = []

file_lock = threading.Lock()
save_file_name = ""

lastDataTime = time.time()


# Function to get the desired unit for the sensor type
def get_unit_from_type(type: str):
    unit = ""
    match type:
        case "Pressure Transducer":
            unit = "psi"
        case "Thermocouple Type T":
            unit = "C"
        case "Thermocouple Type K":
            unit = "C"
        case "Load Cell":
            unit = "lbs"
        case "Voltage" | _:
            unit = "V"
    return unit


def get_unit(channel: int):
    try:
        return get_unit_from_type(daq_sensor_types[daq_channel_numbers.index(channel)])
    except Exception as e:
        print("T7_Pro_Poller, Get Unit   ", channel, daq_channel_numbers)
        return ""


def get_type(channel: int):
    return daq_sensor_types[daq_channel_numbers.index(channel)]


def get_active_channels():
    return daq_channel_numbers


def update_log_name():
    global save_file_name

    this_file_dir = Path(__file__).parent

    t = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_file_name = this_file_dir.parent / "logs" / f"{t}_DAQ_T7_Pro.csv"


def write_headers():
    with file_lock:
        with open(save_file_name, "a") as f:
            f.write("i,Channel #, Sensor Type, Sensor Location\n")
            for i in range(len(daq_channel_numbers)):
                f.write(f"{i},{daq_channel_numbers[i]},{daq_sensor_types[i]},{daq_sensor_locations[i]}\n")
            f.write("#======#\n")
            f.write(f"Start Time: {unixStartTime}\n")
            f.write("#======#\n")
            f.write("Time (s),")
            for i in range(len(daq_channel_numbers)):
                f.write(f"{daq_sensor_locations[i]} [{get_unit_from_type(daq_sensor_types[i])}]")
                if i != len(daq_channel_numbers) - 1:
                    f.write(",")
                else:
                    f.write("\n")


# Function to update the sensor types
def update_config(
    active_channel_numbers,
    active_sensor_types,
    mapping_data,
    active_sensor_locations,
    newScanRate,
):
    global daq_channel_numbers
    global daq_sensor_types
    global daq_sensor_locations
    global daq_mappings
    global processed_buffer
    global scan_rate

    # if daq_channel_numbers != active_channel_numbers and daq_sensor_types != active_sensor_types:
    processed_buffer = []

    daq_channel_numbers = active_channel_numbers
    daq_sensor_types = active_sensor_types
    daq_sensor_locations = active_sensor_locations
    daq_mappings = mapping_data
    scan_rate = newScanRate

    update_log_name()
    write_headers()


# Function to try to make a connection to the T7 over USB, 100ms delay after
def connect_T7():
    global T7_connected
    global T7

    try:
        # Stopping the current stream if we are already connected
        if T7 is not None:
            ljm.eStreamStop(T7)
            ljm.close(T7)
    except:
        pass

    T7 = ljm.openS("T7", "USB", str(SERIAL_NUMBER))  # Any device, Any connection, Any identifier
    time.sleep(0.1)


def configure_T7():
    global cur_stream_daq_sensor_types
    global cur_stream_daq_sensor_numbers
    global cur_stream_daq_sensor_locations
    global cur_stream_daq_mappings
    global cur_stream_scan_rate

    info = ljm.getHandleInfo(T7)
    numAddresses = len(daq_channel_numbers) + 1

    ain_list = []
    for number in daq_channel_numbers:
        ain_list.append(f"AIN{number-1}")
    ain_list.append("AIN14")
    aScanList = ljm.namesToAddresses(numAddresses, ain_list)[0]
    scansPerRead = scan_rate / 2
    # Ensure triggered stream is disabled.
    ljm.eWriteName(T7, "STREAM_TRIGGER_INDEX", 0)
    # Enabling internally-clocked stream.
    ljm.eWriteName(T7, "STREAM_CLOCK_SOURCE", 0)

    aRangeNames = []
    for ain in ain_list:
        aRangeNames.append(f"{ain}_RANGE")
    aRangeNames.append("STREAM_RESOLUTION_INDEX")

    aRangeValues = []
    for sensor in daq_sensor_types:
        aRangeValues.append(0.1 if (sensor == "Thermocouple Type T" or sensor == "Thermocouple Type K") else 10.0)
    aRangeValues.append(10)  # CJC Ain14 range
    aRangeValues.append(8)  # Stream resolution index

    # aRangeValues = [1.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 1, 1, 10, 0]

    # Negative channel and settling configurations do not apply to the T8
    if info[0] == ljm.constants.dtT7:
        #     Negative Channel = 199 (Single-ended)
        #     Settling = 0 (auto)

        for ain in ain_list:
            aRangeNames.append(f"{ain}_NEGATIVE_CH")
            aRangeValues.append(199)
        aRangeNames.append("STREAM_SETTLING_US")
        aRangeValues.append(10)

    numFrames = len(aRangeNames)
    ljm.eWriteNames(T7, numFrames, aRangeNames, aRangeValues)
    actualScanRate = ljm.eStreamStart(T7, int(scansPerRead), int(numAddresses), aScanList, int(scan_rate))

    cur_stream_daq_sensor_types = daq_sensor_types
    cur_stream_daq_sensor_numbers = daq_channel_numbers
    cur_stream_daq_sensor_locations = daq_sensor_locations
    cur_stream_daq_mappings = daq_mappings
    cur_stream_scan_rate = scan_rate


# Retrive the locations of all the sensors
def get_sensor_locations():
    return daq_sensor_locations


# Start the repeated loop of watching for connection to the T7
def start_polling():
    global T7_connected
    global processed_buffer

    global cur_stream_daq_sensor_types
    global cur_stream_daq_sensor_numbers
    global cur_stream_daq_sensor_locations
    global cur_stream_daq_mappings
    global cur_stream_scan_rate

    main_thread = threading.main_thread()

    try:
        while main_thread.is_alive():
            print(T7_connected, "T7_pro")
            if not T7_connected:
                try:
                    # Remove with real data
                    # cur_stream_daq_sensor_types = daq_sensor_types
                    # cur_stream_daq_sensor_numbers = daq_channel_numbers
                    # cur_stream_daq_sensor_locations = daq_sensor_locations
                    # cur_stream_daq_mappings = daq_mappings
                    # cur_stream_scan_rate = scan_rate

                    connect_T7()
                    configure_T7()
                    T7_connected = True

                except Exception as e:
                    print("T7 Pro Poller, connection issue", e)
                    time.sleep(0.5)

            else:
                try:
                    if (
                        (cur_stream_daq_sensor_types != daq_sensor_types)
                        or (cur_stream_daq_sensor_numbers != daq_channel_numbers)
                        or (cur_stream_daq_sensor_locations != daq_sensor_locations)
                        or (cur_stream_daq_mappings != daq_mappings)
                        or (cur_stream_scan_rate != scan_rate)
                    ):

                        T7_connected = False  # This forces the device to re-connect and re-configure
                        processed_buffer = []

                    else:
                        ret = ljm.eStreamRead(T7)
                        aData = ret[0]

                        n = len(daq_channel_numbers) + 1
                        # print([aData[i::n] for i in range(n)])
                        process_data([aData[i::n] for i in range(n)])
                        #
                        # fake_process_data()
                        # time.sleep(0.5)

                except Exception as e:
                    print("T7 Pro Poller Error in process_data", e)
                    # print(traceback.print_exception())
                    time.sleep(0.1)
                    T7_connected = False
    except Exception as e:
        print("T7 Pro big loop:, ", e)
    finally:
        if T7 is not None:
            try:
                ljm.eStreamStop(T7)
            except Exception as e:
                print(f"Error stopping stream: {e}")

            try:
                ljm.close(T7)
            except Exception as e:
                print(f"Error closing device: {e}")


def process_data(read_data):
    global lastDataTime
    global processed_buffer

    # Read data of form:
    #  [
    #     [chan0_sample0, chan0_sample1...]
    #     [chan1_sample0, chan1_sample1...]
    #     ....
    #     [chanN_sample0, chanN_sample1...]
    #  ]

    # Empty buffer to fill with samples of form:
    #  [
    #     [[[chan0_sample0, chan1_sample0, chan2_sample0], time]]
    #     [[[chan0_sample1, chan1_sample1, chan2_sample1], time]]
    #  ]
    processed_samples = [[[0] * len(read_data), 0] for _ in range(len(read_data[0]))]

    # Cold junction approx temp in C
    cold_junction = mean(read_data[-1]) * -92.6 + 467.6 - 273.15

    # Determining the number of reads per channle - to extrapolate to get the exact data read time
    got_data_time = time.time()
    num_samples = len(read_data[-1])

    # Looping through each of the inner sensors from above, besides the CJ temp channel
    for i_sensor in range(len(read_data)):
        if i_sensor != len(read_data) - 1:
            # Looping through each sample read on a specific sensor
            for i_sample in range(len(read_data[i_sensor])):
                try:
                    if daq_sensor_types[i_sensor] == "Thermocouple Type T":
                        try:
                            processed_samples[i_sample][0][i_sensor] = utils.mv_to_c_type_t(
                                read_data[i_sensor][i_sample] * 1000.0 + utils.c_to_mv_type_t(cold_junction)
                            )
                        except ValueError as e:
                            processed_samples[i_sample][0][i_sensor] = 0

                    elif daq_sensor_types[i_sensor] == "Thermocouple Type K":
                        try:
                            processed_samples[i_sample][0][i_sensor] = utils.mv_to_c_type_k(
                                read_data[i_sensor][i_sample] * 1000.0 + utils.c_to_mv_type_k(cold_junction)
                            )
                        except ValueError as e:
                            processed_samples[i_sample][0][i_sensor] = 0

                    elif daq_sensor_types[i_sensor] == "Pressure Transducer" or daq_sensor_types[i_sensor] == "Load Cell":
                        # daq_mappings is of form: ((from V, to V) to (from psi, to psi))
                        slope = (daq_mappings[i_sensor][1][1] - daq_mappings[i_sensor][1][0]) / (
                            daq_mappings[i_sensor][0][1] - daq_mappings[i_sensor][0][0]
                        )
                        yint = (slope * daq_mappings[i_sensor][0][0]) - daq_mappings[i_sensor][1][0]
                        processed_samples[i_sample][0][i_sensor] = read_data[i_sensor][i_sample] * slope - yint
                    else:
                        processed_samples[i_sample][0][i_sensor] = read_data[i_sensor][i_sample]

                except Exception as e:
                    print("T7 Pro Poller, error in processing loop: ", e)
        # On last sensor (CJC read), we'll note the time instead, we just want to do this once per sample,
        else:
            # looping through each sample
            deltaTime = got_data_time - lastDataTime
            for i_sample in range(len(read_data[-1])):
                processed_samples[i_sample][1] = (got_data_time - unixStartTime) - (num_samples - 1 - i_sample) * deltaTime / num_samples

    # Updating the last data time so we can maintain that lovely delta time
    lastDataTime = time.time()

    for sample in processed_samples:
        processed_buffer.append(sample)

    with file_lock:
        with open(save_file_name, "a") as f:
            out_string = ""
            for i_sample in range(len(processed_samples)):
                out_string += str(processed_samples[i_sample][1]) + ","
                for i in range(len(daq_channel_numbers)):
                    out_string += str(processed_samples[i_sample][0][i]) + ","
                out_string = out_string[0:-1] + "\n"

            f.write(out_string)


def fake_process_data():
    processed_buffer.append(
        (
            [math.sin(time.time() - unixStartTime - 0.4 + _) for _ in range(len(daq_channel_numbers))],
            time.time() - unixStartTime - 0.4,
        )
    )
    processed_buffer.append(
        (
            [math.sin(time.time() - unixStartTime - 0.3 + _) for _ in range(len(daq_channel_numbers))],
            time.time() - unixStartTime - 0.3,
        )
    )
    processed_buffer.append(
        (
            [math.sin(time.time() - unixStartTime - 0.2 + _) for _ in range(len(daq_channel_numbers))],
            time.time() - unixStartTime - 0.2,
        )
    )
    processed_buffer.append(
        (
            [math.sin(time.time() - unixStartTime - 0.1 + _) for _ in range(len(daq_channel_numbers))],
            time.time() - unixStartTime - 0.1,
        )
    )
    processed_buffer.append(
        (
            [math.sin(time.time() - unixStartTime + _) for _ in range(len(daq_channel_numbers))],
            time.time() - unixStartTime,
        )
    )


# Get last x seconds of data
def get_data(seconds: float, channel: int):
    x_data = []
    y_data = []

    if len(processed_buffer) > 0 and channel in daq_channel_numbers:
        cur_time = processed_buffer[-1][1]  # time.time() - unixStartTime

        for i in range(len(processed_buffer) - 1, -1, -1):
            if processed_buffer[i][1] > (cur_time - seconds):
                x_data.append(processed_buffer[i][1])
                y_data.append(processed_buffer[i][0][daq_channel_numbers.index(channel)])

        return x_data, y_data
    else:
        return [], []


def get_last_value(channel: int):
    if len(processed_buffer) > 0 and channel in daq_channel_numbers:
        return processed_buffer[-1][0][daq_channel_numbers.index(channel)]
    return 0
