from pathlib import Path
import threading
import time
import serial
from datetime import datetime

ecu_port = "COM7"
ecu_baud = 115200
ecu_serial = None
ecu_connected = False

ecu_command_read_buffer = []
ecu_command_read_buffer_times = []
ecu_command_sent_list = []
ecu_command_sent_list_times = []
ecu_char_read_buffer = ""

# 0 => closed, 1 => open
ecu_valve_desired_states = [0] * 24
ecu_valve_actual_states = [0] * 24
ecu_battery_voltage = 0.0
ecu_pyro_states = [0] * 2



ecu_rs485_valve_percentages = [0] * 12 # creates list 



ecu_valve_locations = ["Not Connected"] * 24

tx_file_lock = threading.Lock()
rx_file_lock = threading.Lock()

rx_file_name = ""
tx_file_name = ""

rs485_poll_enabled = True
last_rs485_poll = time.time()


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

    send_command("{" + str(index) + ",2}")


def open_valve(index: int):
    # send_command("{1," + str(index) + "}")
    global ecu_valve_actual_states
    global ecu_valve_desired_states

    send_command("{" + str(index) + ",1}")


def fire_pyro(index: int):
    ecu_pyro_states[index] = 0 if ecu_pyro_states[index] == 1 else 1
    send_command("{" + str(index) + ",3}")

    def reset_pyro(index: int):
        ecu_pyro_states[index] = 0

    threading.Timer(0.75, reset_pyro, args=(index,)).start()


def poll_rs485():
    send_command("{00,5}")


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
                    ecu_serial = serial.Serial(ecu_port, ecu_baud, timeout=0)
                    ecu_connected = True
                except:
                    ecu_connected = False
                    time.sleep(0.5)
            else:
                # Now that things are connected, read command if there is one
                try:
                    if ecu_serial.in_waiting > 0:
                        data = ecu_serial.read(ecu_serial.in_waiting).decode("utf-8", errors="ignore")

                        ecu_char_read_buffer += data

                        # if data.startswith("{"):
                        #    ecu_char_read_buffer = ""jksdf;jkdsfljkdsf;j;ldlh;hi

                        while "{" in ecu_char_read_buffer and "}" in ecu_char_read_buffer:
                            start = ecu_char_read_buffer.find("{")
                            end = ecu_char_read_buffer.find("}", start)
                            if end != -1 and end > start:
                                command = ecu_char_read_buffer[start : end + 1]  # Include the {} in the command
                                ecu_char_read_buffer = ecu_char_read_buffer[end + 1 :]
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
                    if rs485_poll_enabled and (time.time() - last_rs485_poll) > 0.5:
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

    ecu_command_read_buffer.append(command)
    now = datetime.now()
    command_recieved_time = now.strftime("%H:%M:") + f"{now.second}.{now.microsecond // 10000:02d}"
    ecu_command_read_buffer_times.append(command_recieved_time)

    with rx_file_lock:
        with open(rx_file_name, "a") as f:
            f.write(f"{command_recieved_time},{command}\n")

    # Desired valve state info from ECU
    if command.startswith("{1,") and command.endswith("}"):
        info = command[3:-1].split(",")
        if len(info) == 24:
            for i_state in range(len(info)):
                ecu_valve_desired_states[i_state] = int(info[i_state])

    # Actual valve state info from ECU
    if command.startswith("{2,") and command.endswith("}"):
        info = command[3:-1].split(",")
        if len(info) == 24:
            for i_state in range(len(info)):
                ecu_valve_actual_states[i_state] = int(info[i_state])




    if command.startswith("{4,") and command.endswith("}"):
        info = command[3:-1].split(",") #splits the 12 values 
        for i in range(12):
            try:
                ecu_rs485_valve_percentages[i] = int(info[i]) #stores parsed values 
            except:
                ecu_rs485_valve_percentages[i] = 0






def send_command(command: str):
    global ecu_connected
    global ecu_command_sent_list
    global ecu_command_sent_list_times

    if ecu_connected:
        try:
            out_string = command + "\r\n"
            ecu_serial.write(out_string.encode())

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
        except:
            ecu_connected = False

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


def get_battery_voltage():
    return ecu_battery_voltage


def get_pyro_channel_states():
    return ecu_pyro_states



def get_rs485_valve_percentages():
    return ecu_rs485_valve_percentages