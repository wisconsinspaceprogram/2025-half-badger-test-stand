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


def start_sequence_runner():
    global active_sequence_index
    global active_sequence_step
    global next_step_time

    main_thread = threading.main_thread()

    while main_thread.is_alive():
        if active_sequence_index != -1:
            # Empty / end of sequence check
            if active_sequence_step >= len(sequences[active_sequence_index]):
                active_sequence_index = -1
                active_sequence_step = -1

                ECU_Poller.set_poll_rs485(True)
            else:
                if time.time() > next_step_time:
                    # Execute step here
                    if sequences[active_sequence_index][active_sequence_step][0] == "Open":
                        loc_index = ECU_Poller.get_valve_index(sequences[active_sequence_index][active_sequence_step][1])
                        if loc_index != -1:
                            ECU_Poller.open_valve(loc_index)
                    if sequences[active_sequence_index][active_sequence_step][0] == "Close":
                        loc_index = ECU_Poller.get_valve_index(sequences[active_sequence_index][active_sequence_step][1])
                        if loc_index != -1:
                            ECU_Poller.close_valve(loc_index)

                    if sequences[active_sequence_index][active_sequence_step][0] == "Poll":
                        ECU_Poller.poll_rs485()

                    if sequences[active_sequence_index][active_sequence_step][0] == "Fire":
                        ECU_Poller.fire_pyro(int(sequences[active_sequence_index][active_sequence_step][3][5:6]))

                    if sequences[active_sequence_index][active_sequence_step][0] == "Wait":
                        # Delay setting shit
                        next_step_time = time.time() + sequences[active_sequence_index][active_sequence_step][4]

                    active_sequence_step += 1

        else:
            time.sleep(0.01)
            # print(sequence_names)
            # print(sequences)
