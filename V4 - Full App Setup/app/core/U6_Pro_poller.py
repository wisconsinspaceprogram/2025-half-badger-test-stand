from datetime import datetime
import math
import os
from pathlib import Path
import random
import time
import threading
from statistics import mean

import u6
from thermocouples_reference import thermocouples
import traceback
from core import utils

MAX_BUFFER_SIZE = 1_000_000
MAX_FILE_SIZE = 10_000_000

# Channels are still expressed like the original T7 code:
# [1, 2] means AIN0 and AIN1
daq_channel_numbers = [1, 2]
daq_sensor_types = ["Pressure Transducer", "Thermocouple Type K"]
daq_sensor_locations = ["Combustion Chamber", "IPA Tank Top"]
daq_mappings = [((0, 10), (0, 100)), ((0, 10), (0, 1000))]
scan_rate = 20  # Hz, used only for timing

U6_connected = False
U6 = None

unixStartTime = time.time()
processed_buffer = []
lastDataTime = time.time()
file_lock = threading.Lock()
save_file_name = ""
stop_flag = threading.Event()


# -------------------- UTILITY FUNCTIONS -------------------------


def get_unit_from_type(type: str):
    match type:
        case "Pressure Transducer":
            return "psi"
        case "Thermocouple Type T":
            return "C"
        case "Thermocouple Type K":
            return "C"
        case "Load Cell":
            return "lbs"
        case _:
            return "V"


def get_unit(channel: int):
    try:
        return get_unit_from_type(daq_sensor_types[daq_channel_numbers.index(channel)])
    except:
        print("U6Poller, get_unit issue")
        return ""


def get_type(channel: int):
    return daq_sensor_types[daq_channel_numbers.index(channel)]


def get_active_channels():
    return daq_channel_numbers


def get_sensor_locations():
    return daq_sensor_locations


def update_log_name():
    global save_file_name
    this_file_dir = Path(__file__).parent
    t = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    save_file_name = this_file_dir.parent / "logs" / f"{t}_DAQ_U6.csv"


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


def update_config(active_channel_numbers, active_sensor_types, mapping_data, active_sensor_locations, newScanRate):
    global daq_channel_numbers, daq_sensor_types, daq_sensor_locations, daq_mappings, processed_buffer, scan_rate
    processed_buffer = []
    daq_channel_numbers = active_channel_numbers
    daq_sensor_types = active_sensor_types
    daq_sensor_locations = active_sensor_locations
    daq_mappings = mapping_data
    scan_rate = newScanRate
    update_log_name()
    write_headers()


# -------------------- U6 SETUP -------------------------


def connect_U6():
    global U6, U6_connected
    try:
        if U6 is not None:
            U6.close()
    except:
        pass
    U6 = u6.U6(autoOpen=False)
    U6.open()
    time.sleep(0.1)
    U6_connected = True


# -------------------- POLLING (NO STREAM MODE) -------------------------


def read_ain(channel_index):
    """
    Read a single analog input with max resolution (ResolutionIndex=8)
    SettlingFactor=2
    """
    try:
        return U6.getAIN(positiveChannel=channel_index, resolutionIndex=10, settlingFactor=2)
    except Exception as e:
        print(f"Error reading AIN{channel_index}: {e}")
        return 0


def poll_sensors():
    """
    Poll all channels manually without streaming
    """
    global processed_buffer, lastDataTime

    while not stop_flag.is_set():
        got_data_time = time.time()
        cjc_temp_K = 0
        try:
            cjc_temp_K = U6.getTemperature()
        except:
            pass
        cold_junction = cjc_temp_K - 273.15

        read_data = []
        for ch in daq_channel_numbers:
            raw = read_ain(ch - 1)
            read_data.append([raw])  # wrap in list for compatibility

        # Process data exactly like old stream code
        processed_samples = [[[0] * len(read_data), 0] for _ in range(1)]  # only 1 sample
        for i_sensor in range(len(read_data)):
            try:
                sensor_type = daq_sensor_types[i_sensor]
                raw = read_data[i_sensor][0]
                if sensor_type == "Thermocouple Type T":
                    mv = raw * 1000.0
                    mv += utils.c_to_mv_type_t(cold_junction)
                    processed_samples[0][0][i_sensor] = utils.mv_to_c_type_t(mv)
                elif sensor_type == "Thermocouple Type K":
                    mv = raw * 1000.0
                    mv += utils.c_to_mv_type_k(cold_junction)
                    processed_samples[0][0][i_sensor] = utils.mv_to_c_type_k(mv)
                elif sensor_type in ["Pressure Transducer", "Load Cell"]:
                    slope = (daq_mappings[i_sensor][1][1] - daq_mappings[i_sensor][1][0]) / (
                        daq_mappings[i_sensor][0][1] - daq_mappings[i_sensor][0][0]
                    )
                    yint = (slope * daq_mappings[i_sensor][0][0]) - daq_mappings[i_sensor][1][0]
                    processed_samples[0][0][i_sensor] = raw * slope - yint
                else:
                    processed_samples[0][0][i_sensor] = raw
            except:
                processed_samples[0][0][i_sensor] = 0

        processed_samples[0][1] = got_data_time - unixStartTime
        lastDataTime = got_data_time

        processed_buffer.append(processed_samples[0])
        if len(processed_buffer) > MAX_BUFFER_SIZE:
            processed_buffer = processed_buffer[-MAX_BUFFER_SIZE:]

        # Write to file
        with file_lock:
            with open(save_file_name, "a") as f:
                out = f"{processed_samples[0][1]},"
                out += ",".join(str(val) for val in processed_samples[0][0])
                out += "\n"
                f.write(out)

        # Rotate file if too big
        size_bytes = os.path.getsize(save_file_name)
        if size_bytes > MAX_FILE_SIZE:
            update_log_name()
            write_headers()

        time.sleep(1 / scan_rate)  # wait for next poll


def start_polling():
    if not U6_connected:
        connect_U6()
    polling_thread = threading.Thread(target=poll_sensors, daemon=True)
    polling_thread.start()


# -------------------- PUBLIC DATA ACCESS -------------------------


def get_data(seconds: float, channel: int):
    x_data, y_data = [], []
    if len(processed_buffer) > 0 and channel in daq_channel_numbers:
        cur_time = processed_buffer[-1][1]
        idx = daq_channel_numbers.index(channel)
        for sample in reversed(processed_buffer):
            if sample[1] > cur_time - seconds:
                x_data.append(sample[1])
                y_data.append(sample[0][idx])
            else:
                break
    return x_data, y_data


def get_last_value(channel: int):
    if len(processed_buffer) > 0 and channel in daq_channel_numbers:
        return processed_buffer[-1][0][daq_channel_numbers.index(channel)]
    return 0
