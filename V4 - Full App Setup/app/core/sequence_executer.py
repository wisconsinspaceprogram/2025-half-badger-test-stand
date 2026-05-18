import threading
import time
from core import ECU_Poller

sequence_names = []
sequences = []
active_sequence_index = -1
active_sequence_step = -1
next_step_time = 0
pending_sequence_mode = ""
uploaded_sequence_index = -1


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


def _queue_sequence_request(sequence_index: int, mode: str):
    global active_sequence_index
    global active_sequence_step
    global next_step_time
    global pending_sequence_mode

    if active_sequence_index == -1:
        active_sequence_index = sequence_index
        active_sequence_step = 0
        next_step_time = time.time()
        pending_sequence_mode = mode

        ECU_Poller.set_poll_rs485(False)
        return True

    return False


def run_sequence(sequence_index: int):
    return _queue_sequence_request(sequence_index, "upload_and_start")


def upload_sequence(sequence_index: int):
    return _queue_sequence_request(sequence_index, "upload_only")


def start_uploaded_sequence(sequence_index: int):
    if uploaded_sequence_index != sequence_index:
        print("[SEQUENCE] Selected sequence has not been uploaded. Upload it before starting.")
        return False

    return _queue_sequence_request(sequence_index, "start_only")


def cancel_sequence():
    global active_sequence_index
    global active_sequence_step
    global pending_sequence_mode

    active_sequence_index = -1
    active_sequence_step = -1
    pending_sequence_mode = ""


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
    global pending_sequence_mode
    global uploaded_sequence_index

    main_thread = threading.main_thread()

    while main_thread.is_alive():
        if active_sequence_index != -1:
            try:
                if active_sequence_index >= len(sequences):
                    raise ValueError(f"Invalid active sequence index: {active_sequence_index}")

                request_mode = pending_sequence_mode or "upload_and_start"

                if request_mode in ("upload_only", "upload_and_start"):
                    ecu_steps = _build_ecu_upload_steps(sequences[active_sequence_index])
                    uploaded_sequence_index = -1

                    upload_result = ECU_Poller.upload_sequence_blocking(ecu_steps)

                    if not upload_result.get("success", False):
                        print(f"[SEQUENCE] ECU upload failed: {upload_result}")
                    else:
                        uploaded_sequence_index = active_sequence_index
                        print(f"[SEQUENCE] ECU upload success. steps={upload_result.get('steps_uploaded', 0)}")

                        if request_mode == "upload_and_start":
                            start_result = ECU_Poller.start_uploaded_sequence_blocking()
                            if not start_result.get("success", False):
                                print(f"[SEQUENCE] ECU start failed: {start_result}")
                            else:
                                print("[SEQUENCE] ECU sequence started; resuming polling immediately.")
                        else:
                            print("[SEQUENCE] ECU sequence uploaded and ready to start.")

                elif request_mode == "start_only":
                    if uploaded_sequence_index != active_sequence_index:
                        print("[SEQUENCE] Selected sequence has not been uploaded. Upload it before starting.")
                    else:
                        start_result = ECU_Poller.start_uploaded_sequence_blocking()
                        if not start_result.get("success", False):
                            print(f"[SEQUENCE] ECU start failed: {start_result}")
                        else:
                            print("[SEQUENCE] ECU sequence started; resuming polling immediately.")

            except Exception as e:
                print(f"[SEQUENCE] Failed to process sequence request: {e}")
            finally:
                active_sequence_index = -1
                active_sequence_step = -1
                pending_sequence_mode = ""
                ECU_Poller.set_poll_rs485(True)

        else:
            time.sleep(0.01)
