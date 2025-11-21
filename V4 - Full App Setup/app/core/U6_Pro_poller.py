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
scan_rate = 20  # Hz

cur_stream_daq_sensor_types = daq_sensor_types
cur_stream_daq_sensor_numbers = daq_channel_numbers
cur_stream_daq_sensor_locations = daq_sensor_locations
cur_stream_daq_mappings = daq_mappings
cur_stream_scan_rate = scan_rate

U6_connected = False
U6 = None

unixStartTime = time.time()

processed_buffer = []
lastDataTime = time.time()

file_lock = threading.Lock()
save_file_name = ""

stop_flag = threading.Event()

# -------------------- UNCHANGED: UTILITY FUNCTIONS -------------------------


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

    global daq_channel_numbers
    global daq_sensor_types
    global daq_sensor_locations
    global daq_mappings
    global processed_buffer
    global scan_rate

    processed_buffer = []  # clear buffer

    daq_channel_numbers = active_channel_numbers
    daq_sensor_types = active_sensor_types
    daq_sensor_locations = active_sensor_locations
    daq_mappings = mapping_data
    scan_rate = newScanRate

    update_log_name()
    write_headers()


# -------------------- U6 SETUP + STREAM CONFIG -------------------------


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


def configure_U6():
    global cur_stream_daq_sensor_types
    global cur_stream_daq_sensor_numbers
    global cur_stream_daq_sensor_locations
    global cur_stream_daq_mappings
    global cur_stream_scan_rate
    global U6

    # U6 uses 0-based AIN indexes
    ain_channels = [n - 1 for n in daq_channel_numbers]

    # Build ChannelOptions list per channel
    channel_options = []
    for sensor in daq_sensor_types:
        if sensor.startswith("Thermocouple"):
            # High-gain range for TC amplifier output (±100 mV)
            channel_options.append(2)  # Gain index 2 = 0.1V range
        else:
            # Default ±10V
            channel_options.append(0)

    # --- Stream config ---
    # U6 forces *global* settings for ResolutionIndex + SettlingFactor.
    # Your single-ended config matches ChannelOptions=GAIN.
    U6.streamConfig(
        NumChannels=len(ain_channels),
        ChannelNumbers=ain_channels,
        ChannelOptions=channel_options,
        SettlingFactor=0,
        ResolutionIndex=0,
        ScanFrequency=scan_rate,
    )

    U6.streamStart()

    # Save snapshot
    cur_stream_daq_sensor_types = daq_sensor_types
    cur_stream_daq_sensor_numbers = daq_channel_numbers
    cur_stream_daq_sensor_locations = daq_sensor_locations
    cur_stream_daq_mappings = daq_mappings
    cur_stream_scan_rate = scan_rate


# Retrive the locations of all the sensors
def get_sensor_locations():
    return daq_sensor_locations


def start_polling():
    global U6_connected
    global processed_buffer

    global cur_stream_daq_sensor_types
    global cur_stream_daq_sensor_numbers
    global cur_stream_daq_sensor_locations
    global cur_stream_daq_mappings
    global cur_stream_scan_rate

    main_thread = threading.main_thread()

    try:
        while not stop_flag.is_set():

            if not U6_connected:
                try:
                    connect_U6()
                    configure_U6()
                    U6_connected = True
                except Exception as e:
                    print("U6 Poller, connection issue:", e)
                    time.sleep(0.5)

            else:  # already connected
                try:
                    # Detect config changes (same logic as T7 version)
                    if (
                        cur_stream_daq_sensor_types != daq_sensor_types
                        or cur_stream_daq_sensor_numbers != daq_channel_numbers
                        or cur_stream_daq_sensor_locations != daq_sensor_locations
                        or cur_stream_daq_mappings != daq_mappings
                        or cur_stream_scan_rate != scan_rate
                    ):

                        U6_connected = False
                        processed_buffer = []
                        continue

                    # Read stream packet
                    for result in U6.streamData():
                        if "errors" in result and result["errors"] != 0:
                            print("U6 stream error:", result["errors"])
                            continue

                        if "missed" in result and result["missed"] != 0:
                            print("Missed:", result["missed"])

                        # unpacked dict format
                        data_per_channel = [result[f"AIN{n-1}"] for n in daq_channel_numbers]

                        # data_per_channel is [
                        #   [samples...], [samples...], ...
                        # ]

                        if stop_flag.is_set():
                            print("u6 Pro poller stopping, closing U6 connection...")
                            U6.streamStop()
                            U6.close()
                            print("U6 connection closed.")
                            break

                        process_data(data_per_channel)

                except Exception as e:
                    print("U6 Poller Error:", e)
                    time.sleep(0.2)
                    U6_connected = False

    finally:
        try:
            print("u6 Pro poller stopping, closing U6 connection...")
            U6.streamStop()
            U6.close()
            print("U6 connection closed.")
        except:
            pass


# -------------------- DATA PROCESSING (UNCHANGED LOGIC) -------------------------


def process_data(read_data):
    global lastDataTime
    global processed_buffer

    num_samples = len(read_data[0])

    # NEW: U6 CJ temperature (Kelvin)
    try:
        cjc_temp_K = U6.getTemperature()
        cold_junction = cjc_temp_K - 273.15
    except:
        cold_junction = 25.0  # fallback

    got_data_time = time.time()

    processed_samples = [[[0] * len(read_data), 0] for _ in range(num_samples)]

    for i_sensor in range(len(read_data)):
        for i_sample in range(num_samples):
            try:
                sensor_type = daq_sensor_types[i_sensor]

                if sensor_type == "Thermocouple Type T":
                    mv = read_data[i_sensor][i_sample] * 1000.0
                    mv += utils.c_to_mv_type_t(cold_junction)
                    processed_samples[i_sample][0][i_sensor] = utils.mv_to_c_type_t(mv)

                elif sensor_type == "Thermocouple Type K":
                    mv = read_data[i_sensor][i_sample] * 1000.0
                    mv += utils.c_to_mv_type_k(cold_junction)
                    processed_samples[i_sample][0][i_sensor] = utils.mv_to_c_type_k(mv)

                elif sensor_type in ["Pressure Transducer", "Load Cell"]:
                    slope = (daq_mappings[i_sensor][1][1] - daq_mappings[i_sensor][1][0]) / (
                        daq_mappings[i_sensor][0][1] - daq_mappings[i_sensor][0][0]
                    )
                    yint = (slope * daq_mappings[i_sensor][0][0]) - daq_mappings[i_sensor][1][0]
                    processed_samples[i_sample][0][i_sensor] = read_data[i_sensor][i_sample] * slope - yint

                else:
                    processed_samples[i_sample][0][i_sensor] = read_data[i_sensor][i_sample]

            except:
                processed_samples[i_sample][0][i_sensor] = 0

    # Timestamp reconstruction
    deltaTime = got_data_time - lastDataTime
    for i_sample in range(num_samples):
        processed_samples[i_sample][1] = (got_data_time - unixStartTime) - ((num_samples - 1 - i_sample) * deltaTime / max(num_samples, 1))

    lastDataTime = time.time()

    # Append to buffer
    for sample in processed_samples:
        processed_buffer.append(sample)

    if len(processed_buffer) > MAX_BUFFER_SIZE:
        processed_buffer = processed_buffer[-MAX_BUFFER_SIZE:]

    # Write to file
    with file_lock:
        with open(save_file_name, "a") as f:
            out = ""
            for s in processed_samples:
                out += f"{s[1]},"
                for val in s[0]:
                    out += f"{val},"
                out = out[:-1] + "\n"
            f.write(out)

    # Rotate file if large
    size_bytes = os.path.getsize(save_file_name)
    print(size_bytes, "bytes")

    if size_bytes > MAX_FILE_SIZE:
        update_log_name()
        write_headers()


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
