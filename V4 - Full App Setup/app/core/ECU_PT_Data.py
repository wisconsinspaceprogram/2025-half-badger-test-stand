from pathlib import Path
import threading
import time

MAX_BUFFER_SIZE = 1_000_000
PT_COUNT = 4

unix_start_time = time.time()
pt_file_lock = threading.Lock()
pt_file_name = ""

# [ [pt_values_by_channel], sample_time ]
pt_processed_buffer = []
pt_values = [0.0] * PT_COUNT

pt_enabled = [True] * PT_COUNT
pt_locations = [f"ECU PT{i + 1}" for i in range(PT_COUNT)]
pt_mappings = [((0.0, 5.0), (0.0, 1000.0)) for _ in range(PT_COUNT)]


def set_start_time(start_time: float):
    global unix_start_time
    unix_start_time = start_time


def update_log_name(log_dir: Path, timestamp: str):
    global pt_file_name
    pt_file_name = log_dir / f"{timestamp}_DAQ_ECU_PT.csv"


def write_headers():
    with pt_file_lock:
        with open(pt_file_name, "a") as f:
            f.write("i,Channel #, Sensor Type, Sensor Location\n")
            active_channels = get_active_channels()
            active_locations = get_sensor_locations()
            for i in range(len(active_channels)):
                f.write(f"{i},{active_channels[i]},Pressure Transducer,{active_locations[i]}\n")
            f.write("#======#\n")
            f.write(f"Start Time: {unix_start_time}\n")
            f.write("#======#\n")
            f.write("Time (s)")
            for i in range(len(active_channels)):
                f.write(f",{active_locations[i]} [psi]")
            f.write("\n")


def update_config(enabled_channels, sensor_locations, mappings=None):
    global pt_enabled
    global pt_locations
    global pt_mappings
    global pt_processed_buffer

    pt_processed_buffer = []

    for i in range(PT_COUNT):
        pt_enabled[i] = bool(enabled_channels[i]) if i < len(enabled_channels) else False
        if i < len(sensor_locations) and sensor_locations[i] is not None and sensor_locations[i] != "":
            pt_locations[i] = sensor_locations[i]
        if mappings is not None and i < len(mappings):
            pt_mappings[i] = mappings[i]


def apply_mapping(value: float, mapping):
    try:
        in_min = float(mapping[0][0])
        in_max = float(mapping[0][1])
        out_min = float(mapping[1][0])
        out_max = float(mapping[1][1])
    except Exception:
        return value

    if in_max == in_min:
        return value

    # Match DAQ mapping behavior: ((from V, to V) -> (from eng, to eng)).
    slope = (out_max - out_min) / (in_max - in_min)
    yint = (slope * in_min) - out_min
    return slope * value - yint


def get_active_channels():
    channels = []
    for i in range(PT_COUNT):
        if pt_enabled[i]:
            channels.append(i + 1)
    return channels


def get_sensor_locations():
    locations = []
    for i in range(PT_COUNT):
        if pt_enabled[i]:
            locations.append(pt_locations[i])
    return locations


def parse_pt_frame(command: str):
    global pt_processed_buffer

    if not (command.startswith("{5,") and command.endswith("}")):
        return

    info = command[3:-1].split(",")
    if len(info) < 1:
        return

    try:
        count = min(PT_COUNT, len(info))
        for i in range(count):
            raw_value = float(info[i])
            pt_values[i] = apply_mapping(raw_value, pt_mappings[i])

        sample_time = time.time() - unix_start_time
        pt_processed_buffer.append((pt_values.copy(), sample_time))

        if len(pt_processed_buffer) > MAX_BUFFER_SIZE:
            pt_processed_buffer = pt_processed_buffer[-MAX_BUFFER_SIZE:]

        with pt_file_lock:
            with open(pt_file_name, "a") as f:
                active_channels = get_active_channels()
                row = [str(sample_time)]
                for channel in active_channels:
                    row.append(str(pt_values[channel - 1]))
                f.write(",".join(row) + "\n")
    except ValueError:
        return


def get_data(seconds: float, pt_index: int = 0):
    x_data = []
    y_data = []

    if len(pt_processed_buffer) > 0 and 0 <= pt_index < PT_COUNT:
        cur_time = pt_processed_buffer[-1][1]

        for i in range(len(pt_processed_buffer) - 1, -1, -1):
            if pt_processed_buffer[i][1] > (cur_time - seconds):
                x_data.append(pt_processed_buffer[i][1])
                y_data.append(pt_processed_buffer[i][0][pt_index])

    return x_data, y_data
