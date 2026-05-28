from pathlib import Path
import threading
import time

MAX_BUFFER_SIZE = 1_000_000
TC_COUNT = 4

unix_start_time = time.time()
tc_file_lock = threading.Lock()
tc_file_name = ""

# [ [hot_values_by_channel], sample_time ]
tc_processed_buffer = []
tc_hot_values = [0.0] * TC_COUNT
tc_cold_values = [0.0] * TC_COUNT

tc_enabled = [True] * TC_COUNT
tc_locations = [f"ECU TC{i + 1}" for i in range(TC_COUNT)]


def set_start_time(start_time: float):
    global unix_start_time
    unix_start_time = start_time


def update_log_name(log_dir: Path, timestamp: str):
    global tc_file_name
    tc_file_name = log_dir / f"{timestamp}_DAQ_ECU_TC.csv"


def write_headers():
    with tc_file_lock:
        with open(tc_file_name, "a") as f:
            f.write("i,Channel #, Sensor Type, Sensor Location\n")
            active_channels = get_active_channels()
            active_locations = get_sensor_locations()
            for i in range(len(active_channels)):
                f.write(f"{i},{active_channels[i]},Thermocouple Type K,{active_locations[i]}\n")
            f.write("#======#\n")
            f.write(f"Start Time: {unix_start_time}\n")
            f.write("#======#\n")
            f.write("Time (s)")
            for i in range(len(active_channels)):
                f.write(f",{active_locations[i]} [C]")
            f.write("\n")


def update_config(enabled_channels, sensor_locations):
    global tc_enabled
    global tc_locations
    global tc_processed_buffer

    tc_processed_buffer = []

    for i in range(TC_COUNT):
        tc_enabled[i] = bool(enabled_channels[i]) if i < len(enabled_channels) else False
        if i < len(sensor_locations) and sensor_locations[i] is not None and sensor_locations[i] != "":
            tc_locations[i] = sensor_locations[i]


def get_active_channels():
    channels = []
    for i in range(TC_COUNT):
        if tc_enabled[i]:
            channels.append(i + 1)
    return channels


def get_sensor_locations():
    locations = []
    for i in range(TC_COUNT):
        if tc_enabled[i]:
            locations.append(tc_locations[i])
    return locations


def parse_tc_frame(command: str):
    global tc_processed_buffer

    if not (command.startswith("{6,") and command.endswith("}")):
        return

    info = command[3:-1].split(",")
    if len(info) < 2:
        return

    try:
        pair_count = min(TC_COUNT, len(info) // 2)
        for i in range(pair_count):
            tc_hot_values[i] = float(info[i * 2])
            tc_cold_values[i] = float(info[i * 2 + 1])

        sample_time = time.time() - unix_start_time
        tc_processed_buffer.append((tc_hot_values.copy(), sample_time))

        if len(tc_processed_buffer) > MAX_BUFFER_SIZE:
            tc_processed_buffer = tc_processed_buffer[-MAX_BUFFER_SIZE:]

        with tc_file_lock:
            with open(tc_file_name, "a") as f:
                active_channels = get_active_channels()
                row = [str(sample_time)]
                for channel in active_channels:
                    row.append(str(tc_hot_values[channel - 1]))
                f.write(",".join(row) + "\n")
    except ValueError:
        return


def get_data(seconds: float, tc_index: int = 0, junction: str = "hot"):
    x_data = []
    y_data = []

    if len(tc_processed_buffer) > 0 and 0 <= tc_index < TC_COUNT:
        cur_time = tc_processed_buffer[-1][1]

        for i in range(len(tc_processed_buffer) - 1, -1, -1):
            if tc_processed_buffer[i][1] > (cur_time - seconds):
                x_data.append(tc_processed_buffer[i][1])
                y_data.append(tc_processed_buffer[i][0][tc_index])

    return x_data, y_data
