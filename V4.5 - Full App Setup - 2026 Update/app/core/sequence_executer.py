"""Runs sequences from the PC, one step at a time.

The V4.5 ECU firmware only understands single commands (open / close / fire / poll), so the
sequence is stepped through here and each step is sent as a normal command, exactly like the
manual buttons on the main tab. Wait steps are timed against the sequence start time, so small
delays from sending commands don't add up over a long sequence.
"""
import threading
import time

from core import ECU_Poller

sequence_names = []
sequences = []

HARDCODED_SEQUENCE_SENTINEL = -2

_lock = threading.Lock()
_pending = None            # (index, resolved steps) waiting for the runner thread
_cancel = threading.Event()

active_sequence_index = -1
active_sequence_step = -1
active_sequence_length = 0
next_step_time = 0.0


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


def is_running():
    return active_sequence_index != -1 or _pending is not None


# ---------------------------------------------------------------- building the step list
def _resolve_steps(sequence_steps):
    """Turn the saved steps into (action, target, seconds) tuples, checking every valve
    name against the current valve map BEFORE anything is sent."""
    out = []
    for i, step in enumerate(sequence_steps):
        action, valve_location, custom_location, pyro_channel, delay_seconds = step[:5]

        if action in ("Open", "Close"):
            location = custom_location if valve_location == "Custom" and custom_location else valve_location
            index = ECU_Poller.get_valve_index(location)
            if index < 0 or location in ("", "Not Connected"):
                raise ValueError(f"step {i + 1}: '{location}' is not in the valve map "
                                 f"(Valve Config tab). Fix the sequence or the valve map.")
            out.append((action, index, location))

        elif action == "Wait":
            seconds = max(0.0, float(delay_seconds or 0))
            out.append(("Wait", seconds, ""))

        elif action == "Fire":
            pyro_index = 0
            if isinstance(pyro_channel, str) and pyro_channel.startswith("Pyro "):
                pyro_index = int(pyro_channel.split(" ")[1])
            out.append(("Fire", pyro_index, ""))

        elif action == "Poll":
            out.append(("Poll", 0, ""))

        else:
            raise ValueError(f"step {i + 1}: unsupported action '{action}'")
    return out


# ---------------------------------------------------------------- called from the GUI
def run_sequence(sequence_index: int):
    """Start the sequence now. Returns False (and prints why) if it can't start."""
    global _pending
    if is_running():
        print("[SEQUENCE] A sequence is already running. Cancel it first.")
        return False
    if not (0 <= sequence_index < len(sequences)):
        print(f"[SEQUENCE] Invalid sequence index: {sequence_index}")
        return False
    if not ECU_Poller.ecu_connected:
        print("[SEQUENCE] ECU is not connected - sequence not started.")
        return False
    try:
        steps = _resolve_steps(sequences[sequence_index])
    except ValueError as e:
        print(f"[SEQUENCE] '{sequence_names[sequence_index]}' not started: {e}")
        return False
    if not steps:
        print("[SEQUENCE] Sequence is empty.")
        return False

    _cancel.clear()
    with _lock:
        _pending = (sequence_index, steps)
    return True


def start_hardcoded_launch_sequence():
    # The V4 ECU had a launch sequence built into its firmware (command 33). The V4.5 ECU
    # firmware doesn't, so there is nothing to start.
    print("[SEQUENCE] The V4.5 ECU firmware has no built-in launch sequence. "
          "Make it a sequence on the Sequences tab and run it with Start instead.")
    return False


def cancel_sequence(*_):
    if is_running():
        print("[SEQUENCE] Cancel requested.")
    _cancel.set()


def get_sequence_step():
    return max(active_sequence_step, 0)


def get_sequence_length():
    return active_sequence_length


def get_time_till_next_step():
    if active_sequence_index != -1:
        return max(0.0, next_step_time - time.time())
    return 0


# ---------------------------------------------------------------- runner thread
def _wait_until(deadline):
    """Sleep until `deadline` (time.time()), waking early on cancel. Returns False if cancelled."""
    while True:
        if _cancel.is_set():
            return False
        left = deadline - time.time()
        if left <= 0:
            return True
        time.sleep(min(0.01, left))


def _run(index, steps):
    global active_sequence_index, active_sequence_step, active_sequence_length, next_step_time

    name = sequence_names[index] if index < len(sequence_names) else str(index)
    active_sequence_index = index
    active_sequence_length = len(steps)
    ECU_Poller.set_poll_rs485(False)      # the sequence's own Poll steps decide when to poll
    print(f"[SEQUENCE] Started '{name}' ({len(steps)} steps)")

    t_step = time.time()
    try:
        for i, (action, target, label) in enumerate(steps):
            if _cancel.is_set():
                print(f"[SEQUENCE] '{name}' cancelled before step {i + 1}")
                return
            active_sequence_step = i + 1

            if action == "Wait":
                t_step += target
                next_step_time = t_step
                if not _wait_until(t_step):
                    print(f"[SEQUENCE] '{name}' cancelled during step {i + 1}")
                    return
                continue

            next_step_time = time.time()
            if action == "Open":
                ECU_Poller.open_valve(target)
            elif action == "Close":
                ECU_Poller.close_valve(target)
            elif action == "Fire":
                ECU_Poller.fire_pyro(target)
            elif action == "Poll":
                ECU_Poller.poll_rs485()
            print(f"[SEQUENCE] step {i + 1}/{len(steps)}: {action} {label or target}")

        print(f"[SEQUENCE] '{name}' finished")
    except Exception as e:
        print(f"[SEQUENCE] '{name}' stopped by an error: {e}")
    finally:
        active_sequence_index = -1
        active_sequence_step = -1
        active_sequence_length = 0
        ECU_Poller.set_poll_rs485(True)


def start_sequence_runner():
    global _pending
    main_thread = threading.main_thread()

    while main_thread.is_alive():
        with _lock:
            job, _pending = _pending, None
            if job is not None:
                globals()["active_sequence_index"] = job[0]   # no gap where is_running() is False
        if job is None:
            time.sleep(0.01)
            continue
        _run(*job)