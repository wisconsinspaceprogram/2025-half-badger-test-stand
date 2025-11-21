import threading
import time
import dearpygui.dearpygui as dpg
from gui import tabs, visual_updater
from core import T7_poller, T7_Pro_poller, U6_Pro_poller, ECU_Poller, sequence_executer

dpg.create_context()

U6_thread = None


def main():
    global U6_thread

    # Getting the gui up and running
    with dpg.window(
        tag="Main Window",
        label="Main Window",
        width=1920,
        height=1080,
        no_title_bar=True,
        no_move=True,
    ):
        tabs.build_tabs()
        tabs.load_defaults()

    dpg.create_viewport(title="Kick-ass control app", width=1800, height=1000)

    # Starting the DAQ and ECU pollers to retrive data in the background
    threading.Thread(target=T7_poller.start_polling, daemon=False).start()
    threading.Thread(target=T7_Pro_poller.start_polling, daemon=False).start()
    U6_thread = threading.Thread(target=U6_Pro_poller.start_polling, daemon=False)
    U6_thread.start()
    threading.Thread(target=ECU_Poller.start_ecu_communication, daemon=False).start()
    threading.Thread(target=sequence_executer.start_sequence_runner, daemon=False).start()

    # Starting the GUI update poller that retrives data from the backend and updates the GUI labels and plots
    threading.Thread(target=visual_updater.update_thread, daemon=False).start()

    # Running the GUI:
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("Main Window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    try:
        main()
    finally:
        U6_Pro_poller.stop_flag.set()
