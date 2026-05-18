import threading
import time
from core import ECU_Poller

sequence_names = []
sequences = []
active_sequence_index = -1
active_sequence_step = -1
next_step_time = 0


def update_sequence_steps(new_sequnces):
    global sequences
    sequences = new_sequnces


def update_sequence_names(new_names):
    global sequence_names
    sequence_names = new_names


def get_sequences():
    return sequences


def get_names():
    return sequence_names


def run_sequence(sequence_index: int):
    global active_sequence_index
    global active_sequence_step
    global next_step_time

    if active_sequence_index == -1:
        active_sequence_index = sequence_index
        active_sequence_step = 0
        next_step_time = time.time()

        ECU_Poller.set_poll_rs485(False)


def cancel_sequence():
    global active_sequence_index
    global active_sequence_step

    active_sequence_index = -1
    active_sequence_step = -1


def get_sequence_step():
    return active_sequence_step


def get_sequence_length():
    try:
        if active_sequence_index >= 0:
            return len(sequences[active_sequence_index])
        else:
            return 0
    except:
        return 0


def get_time_till_next_step():
    if active_sequence_index != -1:
        return next_step_time - time.time()
    return 0


def _build_ecu_upload_steps(sequence_steps):
    out_steps = []

    for i, step in enumerate(sequence_steps):
        action_name = step[0]
        valve_location = step[1]
        custom_valve_location = step[2]
        pyro_channel = step[3]
        delay_seconds = step[4]

        if action_name == "Open" or action_name == "Close":
            requested_location = valve_location
            if requested_location == "Custom" and custom_valve_location != "":
                requested_location = custom_valve_location

            loc_index = ECU_Poller.get_valve_index(requested_location)
            if loc_index < 12 or loc_index > 35:
                raise ValueError(f"Invalid valve location at step {i}: {requested_location}")

            action_id = 1 if action_name == "Open" else 2
            out_steps.append((action_id, loc_index, 0))

        elif action_name == "Wait":
            wait_ms = int(float(delay_seconds) * 1000.0)
            if wait_ms < 0:
                wait_ms = 0
            if wait_ms > 60000:
                wait_ms = 60000
            out_steps.append((3, 0, wait_ms))

        elif action_name == "Fire":
            pyro_index = 0
            if isinstance(pyro_channel, str) and pyro_channel.startswith("Pyro "):
                pyro_index = int(pyro_channel.split(" ")[1])
            out_steps.append((4, pyro_index, 0))

        elif action_name == "Poll":
            out_steps.append((5, 0, 0))

        else:
            raise ValueError(f"Unsupported action for ECU upload at step {i}: {action_name}")

    return out_steps


def start_sequence_runner():
    global active_sequence_index
    global active_sequence_step
    global next_step_time

    main_thread = threading.main_thread()

    while main_thread.is_alive():
        if active_sequence_index != -1:
            try:
                if active_sequence_index >= len(sequences):
                    raise ValueError(f"Invalid active sequence index: {active_sequence_index}")

                ecu_steps = _build_ecu_upload_steps(sequences[active_sequence_index])
                result = ECU_Poller.upload_sequence_and_start_blocking(ecu_steps)

                if not result.get("success", False):
                    print(f"[SEQUENCE] ECU upload/start failed: {result}")
                else:
                    print(f"[SEQUENCE] ECU upload/start success. steps={result.get('steps_uploaded', 0)}")

            except Exception as e:
                print(f"[SEQUENCE] Failed to build/upload sequence: {e}")
            finally:
                active_sequence_index = -1
                active_sequence_step = -1
                ECU_Poller.set_poll_rs485(True)

        else:
            time.sleep(0.01)
            # print(sequence_names)
            # print(sequences)
