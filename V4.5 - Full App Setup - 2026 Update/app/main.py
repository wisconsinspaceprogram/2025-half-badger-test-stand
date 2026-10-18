import sys
import threading
import time
import dearpygui.dearpygui as dpg
from gui import tabs, visual_updater, main_tab
from core import T7_poller, T7_Pro_poller, U6_Pro_poller, ECU_Poller, sequence_executer

# --- Display scaling --------------------------------------------------------
# Without this, Windows treats the app as "DPI unaware": at 125% scaling it reports
# a 1920x1080 screen as 1536x864 and then stretches the whole window (blurry, and
# the layout runs off-screen). Being DPI aware gives us real pixels instead.
DPI_AWARE = True

# Optional text size multiplier, e.g. 1.25 on a 125% laptop if the text feels small.
# The main tab re-flows around whatever size things end up being.
FONT_SCALE = 1.0


def _enable_windows_dpi_awareness():
    if sys.platform != "win32" or not DPI_AWARE:
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware (Win 8.1+)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # system DPI aware (older Windows)
        except Exception:
            pass


def _screen_size(default=(1600, 900)):
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass
    return default


_enable_windows_dpi_awareness()  # must happen before any window is created
dpg.create_context()

U6_thread = None


def main():
    global U6_thread

    # Getting the gui up and running
    # No fixed size: as the primary window it always fills the viewport.
    with dpg.window(
        tag="Main Window",
        label="Main Window",
        no_title_bar=True,
        no_move=True,
        horizontal_scrollbar=True,
    ):
        tabs.build_tabs()
        tabs.load_defaults()

    # Start the viewport at the size of the actual screen (it is maximised below)
    screen_w, screen_h = _screen_size()
    dpg.create_viewport(
        title="Kick-ass control app",
        width=min(1800, screen_w),
        height=min(1000, screen_h - 80),
        min_width=1000,
        min_height=600,
    )
    dpg.set_global_font_scale(FONT_SCALE)

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

    # Re-flow the main tab whenever the window changes size, and once the first frames
    # are drawn (the tab bar height is only measurable after that).
    dpg.set_viewport_resize_callback(main_tab.on_viewport_resize)
    dpg.set_frame_callback(2, main_tab.on_viewport_resize)
    dpg.set_frame_callback(5, main_tab.on_viewport_resize)
    dpg.maximize_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    try:
        main()
    finally:
        U6_Pro_poller.stop_flag.set()   