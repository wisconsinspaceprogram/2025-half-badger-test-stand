from pathlib import Path
from collections import deque
import queue
import threading
import time
import serial
from datetime import datetime

ecu_port = "COM4"
ecu_baud = 9600
ecu_serial = None
ecu_connected = False

ecu_command_read_buffer = []
ecu_command_read_buffer_times = []
ecu_command_sent_list = []
ecu_command_sent_list_times = []
ecu_char_read_buffer = ""

DEBUG_ECU_RX = True
DEBUG_ECU_TX = True

POLL_RS485_COMMAND = "{00,5}"
STOP_ECU_SEQUENCE_COMMAND = "{0,21}"
UPLOAD_ECU_SEQUENCE_BEGIN_COMMAND_PREFIX = "{0,30,"
UPLOAD_ECU_SEQUENCE_STEP_COMMAND_PREFIX = "{0,31,"
UPLOAD_ECU_SEQUENCE_START_COMMAND = "{0,32}"
ACK_COMMAND_PREFIX = "{7,"
COMMAND_ACK_TIMEOUT_S = 0.35
COMMAND_MAX_RETRIES = 5
ACK_LATENCY_HISTORY_SIZE = 200
MANUAL_COMMAND_POST_POLL_GAP_S = 1.0

command_queue = queue.Queue()
command_ack_event = threading.Event()
pending_command_ack = None
pending_command_send_time = None
command_worker_started = False
command_worker_lock = threading.Lock()
send_lock = threading.Lock()
command_in_flight = threading.Event()
ack_latency_samples_ms = deque(maxlen=ACK_LATENCY_HISTORY_SIZE)

# 0 => closed, 1 => open
ecu_valve_desired_states = [0] * 36
ecu_valve_actual_states = [0] * 36
ecu_battery_voltage = 0.0
ecu_pyro_states = [0] * 2


ecu_rs485_valve_percentages = [0] * 24  # creates list


ecu_valve_locations = ["Not Connected"] * 36

tx_file_lock = threading.Lock()
rx_file_lock = threading.Lock()

rx_file_name = ""
tx_file_name = ""

rs485_poll_enabled = True
last_rs485_poll = time.time()
last_rs485_poll_sent = 0.0

# Manual command gating: stop polls and wait a strict gap after the last poll TX.
manual_command_window_enabled = True
manual_command_pending_event = threading.Event()
manual_pending_commands = queue.Queue()
manual_pending_worker_started = False
manual_pending_worker_lock = threading.Lock()
telemetry_frame_seen = {
    1: False,
    2: False,
    3: False,
    4: False,
    5: False,
    6: False,
}


def update_log_names():
    global rx_file_name
    global tx_file_name

    this_file_dir = Path(__file__).parent

    t = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    rx_file_name = this_file_dir.parent / "logs" / f"{t}_ECU_RX.csv"
    tx_file_name = this_file_dir.parent / "logs" / f"{t}_ECU_TX.csv"


def write_headers():
    with tx_file_lock:
        with open(tx_file_name, "a") as f:
            for i in range(len(ecu_valve_locations)):
                f.write(f"{i},{ecu_valve_locations[i]}\n")
            f.write("#======#\n")

    with rx_file_lock:
        with open(rx_file_name, "a") as f:
            for i in range(len(ecu_valve_locations)):
                f.write(f"{i},{ecu_valve_locations[i]}\n")
            f.write("#======#\n")


def update_valve_locations(new_locations):
    global ecu_valve_locations
    ecu_valve_locations = new_locations

    update_log_names()
    write_headers()


def update_port_settings(port: str, baud: int):
    global ecu_port
    global ecu_baud
    global ecu_connected

    ecu_port = port
    ecu_baud = baud

    ecu_connected = False


def get_valve_locations():
    return ecu_valve_locations


def close_valve(index: int):
    # send_command("{2," + str(index) + "}")
    global ecu_valve_actual_states
    global ecu_valve_desired_states

    queue_manual_command_after_telemetry("{" + str(index) + ",2}")


def close_valve_blocking(index: int, retries: int = COMMAND_MAX_RETRIES):
    return queue_command_and_wait("{" + str(index) + ",2}", retries=retries)


def open_valve(index: int):
    # send_command("{1," + str(index) + "}")
    global ecu_valve_actual_states
    global ecu_valve_desired_states

    queue_manual_command_after_telemetry("{" + str(index) + ",1}")


def open_valve_blocking(index: int, retries: int = COMMAND_MAX_RETRIES):
    return queue_command_and_wait("{" + str(index) + ",1}", retries=retries)


def fire_pyro(index: int):
    ecu_pyro_states[index] = 0 if ecu_pyro_states[index] == 1 else 1
    queue_manual_command_after_telemetry("{" + str(index) + ",3}")

    def reset_pyro(index: int):
        ecu_pyro_states[index] = 0

    threading.Timer(0.75, reset_pyro, args=(index,)).start()


def fire_pyro_blocking(index: int, retries: int = COMMAND_MAX_RETRIES):
    ecu_pyro_states[index] = 0 if ecu_pyro_states[index] == 1 else 1
    result = queue_command_and_wait("{" + str(index) + ",3}", retries=retries)

    def reset_pyro(index: int):
        ecu_pyro_states[index] = 0

    threading.Timer(0.75, reset_pyro, args=(index,)).start()
    return result


def poll_rs485():
    # Poll commands should use the queue to ensure reliable delivery with retries
    # But don't wait for ACK since polling is informational
    queue_command(POLL_RS485_COMMAND, retries=3)


def upload_sequence_blocking(steps, retries: int = COMMAND_MAX_RETRIES):
    if steps is None or len(steps) == 0:
        return {
            "success": False,
            "stage": "validate",
            "reason": "empty sequence",
        }

    # Stop any running ECU-side sequence before uploading a new one.
    stop_ecu_sequence_blocking(retries=retries)

    begin_cmd = f"{UPLOAD_ECU_SEQUENCE_BEGIN_COMMAND_PREFIX}{len(steps)}}}"
    print(f"[SEQUENCE] Uploading begin cmd: {begin_cmd} (len={len(begin_cmd)})")
    begin_result = queue_command_and_wait(begin_cmd, retries=retries)
    if not begin_result.get("success", False):
        print(f"[SEQUENCE] Begin command failed: {begin_result}")
        begin_result["stage"] = "begin"
        return begin_result

    last_step_result = None
    for i, step in enumerate(steps):
        action = int(step[0])
        target = int(step[1])
        value = int(step[2])
        step_cmd = f"{UPLOAD_ECU_SEQUENCE_STEP_COMMAND_PREFIX}{i},{action},{target},{value}}}"
        print(f"[SEQUENCE] Step {i}: {step_cmd} (action={action}, target={target}, value={value})")
        step_result = queue_command_and_wait(step_cmd, retries=retries)
        if not step_result.get("success", False):
            print(f"[SEQUENCE] Step {i} command failed: {step_result}")
            step_result["stage"] = "step"
            step_result["step_index"] = i
            step_result["step"] = [action, target, value]
            return step_result
        last_step_result = step_result

    return {
        "success": True,
        "steps_uploaded": len(steps),
        "begin": begin_result,
        "last_step": last_step_result,
    }


def start_uploaded_sequence_blocking(retries: int = COMMAND_MAX_RETRIES):
    print(f"[SEQUENCE] All steps uploaded, sending start cmd: {UPLOAD_ECU_SEQUENCE_START_COMMAND}")
    start_result = queue_command_and_wait(UPLOAD_ECU_SEQUENCE_START_COMMAND, retries=retries)
    if not start_result.get("success", False):
        print(f"[SEQUENCE] Start command failed: {start_result}")
        start_result["stage"] = "start"
        return start_result

    return {
        "success": True,
        "start": start_result,
    }


def upload_sequence_and_start_blocking(steps, retries: int = COMMAND_MAX_RETRIES):
    upload_result = upload_sequence_blocking(steps, retries=retries)
    if not upload_result.get("success", False):
        return upload_result

    start_result = start_uploaded_sequence_blocking(retries=retries)
    if not start_result.get("success", False):
        return start_result

    return {
        "success": True,
        "steps_uploaded": len(steps),
        "begin": upload_result.get("begin"),
        "last_step": upload_result.get("last_step"),
        "start": start_result.get("start"),
    }


def stop_ecu_sequence():
    queue_command(STOP_ECU_SEQUENCE_COMMAND)


def stop_ecu_sequence_blocking(retries: int = COMMAND_MAX_RETRIES):
    return queue_command_and_wait(STOP_ECU_SEQUENCE_COMMAND, retries=retries)


def parse_command_fields(command: str):
    if not (command.startswith("{") and command.endswith("}")):
        return None

    parts = command[1:-1].split(",")
    if len(parts) < 2:
        return None

    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def start_command_worker():
    global command_worker_started

    with command_worker_lock:
        if command_worker_started:
            return

        threading.Thread(target=command_worker_loop, daemon=True).start()
        command_worker_started = True


def queue_command(command: str, retries: int = COMMAND_MAX_RETRIES):
    start_command_worker()
    command_queue.put((command, retries))


def clear_pending_poll_commands():
    cleared = 0

    with command_queue.mutex:
        kept_items = deque()
        while command_queue.queue:
            item = command_queue.queue.popleft()
            command_text = item[0] if len(item) > 0 else None
            if command_text == POLL_RS485_COMMAND:
                cleared += 1
            else:
                kept_items.append(item)

        if cleared > 0:
            command_queue.queue = kept_items
            command_queue.unfinished_tasks = max(0, command_queue.unfinished_tasks - cleared)
            command_queue.not_full.notify_all()
            if command_queue.unfinished_tasks == 0:
                command_queue.all_tasks_done.notify_all()

    if cleared > 0 and DEBUG_ECU_TX:
        print(f"[ECU_TX] cleared {cleared} queued poll command(s) before manual send")


def reset_telemetry_block_tracking():
    for k in telemetry_frame_seen:
        telemetry_frame_seen[k] = False


def mark_telemetry_frame(frame_id: int):
    if frame_id in telemetry_frame_seen:
        telemetry_frame_seen[frame_id] = True

    if all(telemetry_frame_seen.values()):
        if DEBUG_ECU_RX:
            print("[ECU_RX] telemetry block complete")
        reset_telemetry_block_tracking()


def queue_manual_command_after_telemetry(command: str, retries: int = COMMAND_MAX_RETRIES):
    if not manual_command_window_enabled:
        queue_command(command, retries=retries)
        return

    # Immediately block new poll scheduling so the command gets a quieter link.
    manual_command_pending_event.set()
    clear_pending_poll_commands()
    _start_manual_pending_worker()
    manual_pending_commands.put((command, retries))


def _start_manual_pending_worker():
    global manual_pending_worker_started

    with manual_pending_worker_lock:
        if manual_pending_worker_started:
            return

        threading.Thread(target=_manual_pending_worker_loop, daemon=True).start()
        manual_pending_worker_started = True


def _manual_pending_worker_loop():
    while True:
        command, retries = manual_pending_commands.get()
        try:
            while command_in_flight.is_set():
                time.sleep(0.005)

            while (time.time() - last_rs485_poll_sent) < MANUAL_COMMAND_POST_POLL_GAP_S:
                time.sleep(0.005)

            result = queue_command_and_wait(command, retries=retries)
            if DEBUG_ECU_TX and not result.get("success", False):
                print(f"[ECU_TX] manual command failed after poll-gap wait: {result}")
        finally:
            manual_command_pending_event.clear()
            manual_pending_commands.task_done()


def queue_command_and_wait(command: str, retries: int = COMMAND_MAX_RETRIES, timeout_s: float = None):
    start_command_worker()
    completion_event = threading.Event()
    completion_result = {
        "success": False,
        "attempts": 0,
        "duration_ms": 0.0,
        "timed_out": False,
    }
    command_queue.put((command, retries, completion_event, completion_result))

    if timeout_s is None:
        timeout_s = max(1.0, retries * COMMAND_ACK_TIMEOUT_S + 0.5)

    completed = completion_event.wait(timeout_s)
    if not completed:
        return {
            "success": False,
            "attempts": completion_result["attempts"],
            "duration_ms": timeout_s * 1000.0,
            "timed_out": True,
        }

    return completion_result


def command_worker_loop():
    global pending_command_ack
    global pending_command_send_time
    global last_rs485_poll_sent

    while True:
        item = command_queue.get()
        if len(item) >= 4:
            command, retries, completion_event, completion_result = item
        else:
            command, retries = item
            completion_event = None
            completion_result = None

        started_at = time.perf_counter()
        attempts = 0
        success = False
        parsed = parse_command_fields(command)

        # Poll commands ({00,5}) don't need ACK verification, just send once
        if command == POLL_RS485_COMMAND:
            last_rs485_poll_sent = time.time()
            send_command(command)
            success = True
            if DEBUG_ECU_TX:
                print(f"[ECU_TX poll] sent")
            if completion_result is not None:
                completion_result["success"] = success
                completion_result["attempts"] = attempts
                completion_result["duration_ms"] = (time.perf_counter() - started_at) * 1000.0
                completion_result["timed_out"] = False
            if completion_event is not None:
                completion_event.set()
            command_queue.task_done()
            continue

        if parsed is None:
            send_command(command)
            success = True
            if completion_result is not None:
                completion_result["success"] = success
                completion_result["attempts"] = attempts
                completion_result["duration_ms"] = (time.perf_counter() - started_at) * 1000.0
                completion_result["timed_out"] = False
            if completion_event is not None:
                completion_event.set()
            command_queue.task_done()
            continue

        pending_command_ack = parsed
        pending_command_send_time = None
        command_ack_event.clear()
        command_in_flight.set()

        try:
            for _ in range(retries):
                attempts += 1
                pending_command_send_time = time.perf_counter()
                send_command(command)
                if command_ack_event.wait(COMMAND_ACK_TIMEOUT_S):
                    success = True
                    break
            else:
                print(f"Command ack timeout: {command}")
        finally:
            pending_command_ack = None
            pending_command_send_time = None
            command_ack_event.clear()
            command_in_flight.clear()
            if completion_result is not None:
                completion_result["success"] = success
                completion_result["attempts"] = attempts
                completion_result["duration_ms"] = (time.perf_counter() - started_at) * 1000.0
                completion_result["timed_out"] = not success
            if completion_event is not None:
                completion_event.set()
            command_queue.task_done()


def set_poll_rs485(enabled: bool):
    global rs485_poll_enabled
    rs485_poll_enabled = enabled


def get_valve_index(location: str):
    try:
        return ecu_valve_locations.index(location)
    except:
        return -1


def start_ecu_communication():
    global ecu_connected
    global ecu_serial
    global ecu_char_read_buffer
    global last_rs485_poll

    main_thread = threading.main_thread()
    start_command_worker()
    try:
        while main_thread.is_alive():
            # process_command("{5,1,2,2,2}")
            # Try reconnecting to the ECU if not connected
            if not ecu_connected or ecu_serial == None:
                print("ecu_connecting")
                try:
                    try:
                        ecu_serial.close()
                    except:
                        # ecu_serial is not assigned, so this will fail
                        pass
                    ecu_serial = serial.Serial(ecu_port, ecu_baud, timeout=0.05, rtscts=False, dsrdtr=False, xonxoff=False)
                    ecu_serial.dtr = False
                    ecu_serial.rts = False
                    ecu_serial.reset_input_buffer()
                    ecu_serial.reset_output_buffer()
                    ecu_connected = True
                    last_rs485_poll = time.time()  # Reset poll timer on successful connection
                    print(f"[ECU_TX] connected to {ecu_port} @ {ecu_baud}")
                    print(f"[ECU_TX] port open={ecu_serial.is_open} name={ecu_serial.port} DTR={ecu_serial.dtr} RTS={ecu_serial.rts}")
                except Exception as connect_error:
                    ecu_connected = False
                    print(f"[ECU_TX] failed to connect to {ecu_port} @ {ecu_baud}: {connect_error}")
                    time.sleep(0.5)
            else:
                # Now that things are connected, read command if there is one
                try:
                    # Blocking read with 50ms timeout to catch any available data
                    data = ecu_serial.read(256)
                    
                    if data:
                        if DEBUG_ECU_RX:
                            print(f"[ECU_RX raw] {data!r}")
                        ecu_char_read_buffer += data.decode("utf-8", errors="ignore")

                        if DEBUG_ECU_RX:
                            print(f"[ECU_RX buffer] {ecu_char_read_buffer!r}")

                        # if data.startswith("{"):
                        #    ecu_char_read_buffer = ""jksdf;jkdsfljkdsf;j;ldlh;hi

                        while "{" in ecu_char_read_buffer and "}" in ecu_char_read_buffer:
                            start = ecu_char_read_buffer.find("{")
                            end = ecu_char_read_buffer.find("}", start)
                            if end != -1 and end > start:
                                command = ecu_char_read_buffer[start : end + 1]  # Include the {} in the command
                                ecu_char_read_buffer = ecu_char_read_buffer[end + 1 :]
                                if DEBUG_ECU_RX:
                                    print(f"[ECU_RX frame] {command}")
                                process_command(command)
                            else:
                                break
                    else:
                        time.sleep(0.01)

                except Exception as e:
                    print("ECU Poller, error collection command", e)
                    ecu_connected = False
                    time.sleep(0.1)

                # Try polling the rs485 valves if that isn't disabled
                try:
                    if (
                        rs485_poll_enabled
                        and not manual_command_pending_event.is_set()
                        and not command_in_flight.is_set()
                        and command_queue.empty()
                        and (time.time() - last_rs485_poll) > 0.5
                    ):
                        last_rs485_poll = time.time()
                        poll_rs485()

                except Exception as e:
                    print("RS 485 Polling error, error collection command", e)
                    time.sleep(0.1)

    except Exception as e:
        print("ECU Main loop: ", e)
    finally:
        try:
            ecu_serial.close()
        except:
            pass


def process_command(command: str):
    global ecu_valve_desired_states
    global ecu_valve_actual_states
    global ecu_battery_voltage
    global pending_command_ack
    global pending_command_send_time

    ecu_command_read_buffer.append(command)
    now = datetime.now()
    command_recieved_time = now.strftime("%H:%M:") + f"{now.second}.{now.microsecond // 10000:02d}"
    ecu_command_read_buffer_times.append(command_recieved_time)

    if DEBUG_ECU_RX:
        print(f"[ECU_RX parsed] {command_recieved_time} {command}")

    with rx_file_lock:
        with open(rx_file_name, "a") as f:
            f.write(f"{command_recieved_time},{command}\n")

    if command.startswith(ACK_COMMAND_PREFIX) and command.endswith("}"):
        # ACK format is {7,address,command} — extract fields 1 and 2
        try:
            parts = command[1:-1].split(",")  # strips { and }
            ack_addr = int(parts[1])
            ack_cmd = int(parts[2])
            parsed = (ack_addr, ack_cmd)
        except (IndexError, ValueError):
            parsed = None
        if parsed is not None and pending_command_ack == parsed:
            latency_ms = None
            if pending_command_send_time is not None:
                latency_ms = (time.perf_counter() - pending_command_send_time) * 1000.0
                ack_latency_samples_ms.append(latency_ms)
            if DEBUG_ECU_RX:
                print(f"[ECU_RX ack matched] {parsed}")
                if latency_ms is not None:
                    print(f"[ECU_RX ack latency] {latency_ms:.1f} ms ({get_ack_latency_stats_string()})")
            command_ack_event.set()
        elif DEBUG_ECU_RX:
            print(f"[ECU_RX ack ignored] pending={pending_command_ack} parsed={parsed}")
        return

    # Desired valve state info from ECU (12 RS485 valves, addresses 12-23)
    # ECU array index 0 = valve address 12, so store at offset +12
    if command.startswith("{1,") and command.endswith("}"):
        info = command[3:-1].split(",")
        for i_state in range(min(len(info), 12)):
            try:
                ecu_valve_desired_states[i_state + 12] = int(info[i_state])
            except:
                ecu_valve_desired_states[i_state + 12] = 0
        if DEBUG_ECU_RX:
            print(f"[ECU_RX desired valve state] {len(info)} values")
        mark_telemetry_frame(1)

    # Actual valve state info from ECU (24 RS485 valves, addresses 12-35)
    # ECU array index 0 = valve address 12, so store at offset +12
    if command.startswith("{2,") and command.endswith("}"):
        info = command[3:-1].split(",")
        for i_state in range(min(len(info), 24)):
            try:
                ecu_valve_actual_states[i_state + 12] = int(info[i_state])
            except:
                ecu_valve_actual_states[i_state + 12] = 0
        if DEBUG_ECU_RX:
            print(f"[ECU_RX actual valve state] {len(info)} values")
        mark_telemetry_frame(2)

    if command.startswith("{4,") and command.endswith("}"):
        info = command[3:-1].split(",")  # splits the 24 RS485 valve values
        for i in range(min(len(info), len(ecu_rs485_valve_percentages))):
            try:
                ecu_rs485_valve_percentages[i] = int(info[i])  # stores parsed values
            except:
                ecu_rs485_valve_percentages[i] = 0
        if DEBUG_ECU_RX:
            print(f"[ECU_RX rs485 percentage frame received] {len(info)} values")
        mark_telemetry_frame(4)

    if command.startswith("{3,") and command.endswith("}"):
        try:
            ecu_battery_voltage = float(command[3:-1])
            if DEBUG_ECU_RX:
                print(f"[ECU_RX battery] {ecu_battery_voltage}")
            mark_telemetry_frame(3)
        except ValueError:
            pass

    if command.startswith("{5,") and command.endswith("}"):
        mark_telemetry_frame(5)

    if command.startswith("{6,") and command.endswith("}"):
        mark_telemetry_frame(6)


ecu_consecutive_write_failures = 0

def send_command(command: str):
    global ecu_connected
    global ecu_command_sent_list
    global ecu_command_sent_list_times
    global ecu_consecutive_write_failures

    if ecu_connected:
        try:
            out_string = command + "\r\n"
            if DEBUG_ECU_TX:
                print(f"[ECU_TX] sending {out_string!r}")
            ecu_serial.write(out_string.encode())
            ecu_consecutive_write_failures = 0

            now = datetime.now()
            command_recieved_time = now.strftime("%H:%M:") + f"{now.second}.{now.microsecond // 10000:02d}"
            ecu_command_sent_list.append(command)
            ecu_command_sent_list_times.append(command_recieved_time)

            if len(ecu_command_sent_list) > 100:
                ecu_command_sent_list = ecu_command_sent_list[-100:]
            if len(ecu_command_sent_list_times) > 100:
                ecu_command_sent_list_times = ecu_command_sent_list_times[-100:]

            with tx_file_lock:
                with open(tx_file_name, "a") as f:
                    f.write(f"{command_recieved_time},{command}\n")
        except Exception as e:
            ecu_consecutive_write_failures += 1
            if DEBUG_ECU_TX:
                print(f"[ECU_TX] write failed for {command} ({ecu_consecutive_write_failures}): {e}")
            if ecu_consecutive_write_failures >= 3:
                ecu_connected = False
                ecu_consecutive_write_failures = 0

        time.sleep(0.005)


def get_last_sent_commands(n: int):
    out = []
    length = len(ecu_command_sent_list_times)
    if length == 0:
        return []
    for i in range(min(n, length)):
        try:
            out.append((ecu_command_sent_list[length - 1 - i], ecu_command_sent_list_times[length - 1 - i]))
        except Exception as e:
            print(e)

    return out


def get_last_recieved_commands(n: int):
    out = []
    length = len(ecu_command_read_buffer)
    if length == 0:
        return []
    for i in range(min(n, length)):
        out.append((ecu_command_read_buffer[length - 1 - i], ecu_command_read_buffer_times[length - 1 - i]))

    return out


def get_desired_valve_states():
    return ecu_valve_desired_states


def get_actual_valve_states():
    return ecu_valve_actual_states


def get_ack_latency_stats():
    samples = list(ack_latency_samples_ms)
    if len(samples) == 0:
        return {
            "count": 0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "min_ms": 0.0,
            "max_ms": 0.0,
        }

    sorted_samples = sorted(samples)
    count = len(sorted_samples)
    p50_index = int(round((count - 1) * 0.50))
    p95_index = int(round((count - 1) * 0.95))

    return {
        "count": count,
        "mean_ms": sum(sorted_samples) / count,
        "p50_ms": sorted_samples[p50_index],
        "p95_ms": sorted_samples[p95_index],
        "min_ms": sorted_samples[0],
        "max_ms": sorted_samples[-1],
    }


def get_ack_latency_stats_string():
    stats = get_ack_latency_stats()
    if stats["count"] == 0:
        return "n=0"

    return (
        f"n={stats['count']} "
        f"avg={stats['mean_ms']:.1f}ms "
        f"p50={stats['p50_ms']:.1f}ms "
        f"p95={stats['p95_ms']:.1f}ms"
    )


def get_battery_voltage():
    return ecu_battery_voltage


def get_pyro_channel_states():
    return ecu_pyro_states


def get_rs485_valve_percentages():
    return ecu_rs485_valve_percentages
