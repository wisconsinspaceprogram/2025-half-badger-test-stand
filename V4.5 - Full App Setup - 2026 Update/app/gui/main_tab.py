import dearpygui.dearpygui as dpg
from core import ECU_Poller, sequence_executer
from gui import pnid_setups

pnid_data_tags = []
pnid_valve_tags = []

possible_valve_locations = []
possible_sensor_locations = []

# ---------------------------------------------------------------------------
# Layout tuning
#
# Nothing on this tab uses absolute screen positions any more. The tab is three
# columns (valves | P&ID + console/pyro/sequence | plots) whose sizes are worked
# out from the current window size in on_viewport_resize(). That way it fits on
# any monitor and at any Windows display scaling (100%, 125%, 150%...).
# ---------------------------------------------------------------------------
GAP = 8                    # space between panels
VALVE_COL_FRAC = 0.21      # share of the width for the valve table
PLOT_COL_FRAC = 0.33       # share of the width for the plots
VALVE_COL_MIN, VALVE_COL_MAX = 300, 400
PLOT_COL_MIN, PLOT_COL_MAX = 340, 800
CONTROL_COL_W = 270        # pyro + sequence panel beside the ECU console
BOTTOM_ROW_MIN, BOTTOM_ROW_MAX = 260, 360  # ECU console / pyro / sequence row height
PNID_MAX_SCALE = 1.6       # don't blow the P&ID up past this on very big screens
PLOT_MIN_H = 140

_content_top = 40          # y where the tab content starts; measured after the first frame


def get_pnid_data_tags():
    return pnid_data_tags


def get_pnid_valve_tags():
    return pnid_valve_tags


def arm_pyro_channels(sender, app_data, user_data):
    if app_data:
        dpg.show_item("pyro_fire_button_0")
        dpg.show_item("pyro_fire_button_1")
    else:
        dpg.hide_item("pyro_fire_button_0")
        dpg.hide_item("pyro_fire_button_1")


def callback_open_valve(sender, app_data, user_data):
    ECU_Poller.open_valve(user_data)


def callback_close_valve(sender, app_data, user_data):
    ECU_Poller.close_valve(user_data)


def callback_fire_pyro(sender, app_data, user_data):
    ECU_Poller.fire_pyro(user_data)


def callback_send_command(sender, app_data, user_data):
    command = dpg.get_value(user_data)
    if command != "":
        ECU_Poller.send_command(command)


def callback_start_sequence(sender, app_data, user_data):
    selected_sequence = dpg.get_value(user_data)
    if selected_sequence not in sequence_executer.get_names():
        print("[SEQUENCE] Select a valid sequence before starting.")
        return

    index = sequence_executer.get_names().index(selected_sequence)
    sequence_executer.start_uploaded_sequence(index)


def callback_upload_sequence(sender, app_data, user_data):
    selected_sequence = dpg.get_value(user_data)
    if selected_sequence not in sequence_executer.get_names():
        print("[SEQUENCE] Select a valid sequence before uploading.")
        return

    index = sequence_executer.get_names().index(selected_sequence)
    sequence_executer.upload_sequence(index)


def callback_start_hardcoded_launch_sequence(sender, app_data, user_data):
    sequence_executer.start_hardcoded_launch_sequence()


def callback_stop_sequence():
    sequence_executer.cancel_sequence()


def get_possible_valve_locations():
    return possible_valve_locations


def get_possible_sensor_locations():
    return possible_sensor_locations


def _clamp(value, low, high):
    return max(low, min(high, value))


def on_viewport_resize(sender=None, app_data=None, user_data=None):
    """Size every panel on the main tab to fit the current window.

    Hooked up in main.py to the viewport resize callback (and run once after the
    first frames), so it also runs when the window is maximised or dragged to a
    monitor with a different size / scaling.
    """
    global _content_top

    if not dpg.does_item_exist("main_tab_columns"):
        return

    vw = dpg.get_viewport_client_width()
    vh = dpg.get_viewport_client_height()
    if vw <= 0 or vh <= 0:
        return  # minimised

    # Where the tab content actually starts (below the tab bar). Only measurable once drawn
    # and while the Home tab is showing; otherwise keep the last good value.
    top = dpg.get_item_rect_min("main_tab_columns")[1]
    if 0 < top < vh:
        _content_top = top

    window_pad = 8
    avail_w = vw - 2 * window_pad
    avail_h = vh - _content_top - window_pad - 4

    # --- column widths ---
    valve_w = _clamp(int(avail_w * VALVE_COL_FRAC), VALVE_COL_MIN, VALVE_COL_MAX)
    plot_w = _clamp(int(avail_w * PLOT_COL_FRAC), PLOT_COL_MIN, PLOT_COL_MAX)
    center_w = max(CONTROL_COL_W + 250 + GAP, avail_w - valve_w - plot_w - 2 * GAP)

    # --- left: valve table (scrolls if the screen is short) ---
    dpg.configure_item("main_tab_valve_panel", width=valve_w, height=avail_h)

    # --- centre: P&ID on top, console / pyro / sequence below ---
    bottom_h = _clamp(int(avail_h * 0.32), BOTTOM_ROW_MIN, BOTTOM_ROW_MAX)
    pnid_h = max(200, avail_h - bottom_h - GAP)
    scale = min(center_w, pnid_h) / pnid_setups.PNID_BASE_SIZE
    scale = min(scale, PNID_MAX_SCALE)
    pnid_size = pnid_setups.PNID_BASE_SIZE * scale

    dpg.configure_item("main_tab_pnid_panel", width=center_w, height=pnid_h)
    pnid_setups.rescale_pnid(scale, origin=((center_w - pnid_size) // 2, 0))

    dpg.configure_item("main_tab_ecu_panel", width=center_w - CONTROL_COL_W - GAP, height=bottom_h)
    dpg.configure_item("main_tab_control_panel", width=CONTROL_COL_W, height=bottom_h)

    # Received-commands box takes ~40% of the console height; the sent box fills the rest (height=-1)
    dpg.configure_item("main_tab_ecu_recieved_commands", height=max(60, int(bottom_h * 0.38)))

    # --- right: plot controls + two plots sharing the remaining height ---
    dpg.configure_item("main_tab_plot_panel", width=plot_w, height=avail_h)
    controls_h = dpg.get_item_rect_size("main_tab_plot_controls")[1] or 130
    plot_h = max(PLOT_MIN_H, int((avail_h - controls_h - 3 * GAP) / 2))
    dpg.configure_item("pt_lc_plot", height=plot_h)
    dpg.configure_item("tc_v_plot", height=plot_h)


def build():
    global pnid_data_tags, pnid_valve_tags, possible_valve_locations, possible_sensor_locations

    def set_lookback_value(sender, app_data, user_data):
        dpg.set_value("main_tab_seconds_lookback", user_data)

    def set_plot_autofit(sender, app_data, user_data):
        dpg.configure_item("x_axis_1", auto_fit=app_data)
        dpg.configure_item("y_axis_psi", auto_fit=app_data)
        dpg.configure_item("y_axis_lbs", auto_fit=app_data)
        dpg.configure_item("x_axis_2", auto_fit=app_data)
        dpg.configure_item("y_axis_c", auto_fit=app_data)
        dpg.configure_item("y_axis_v", auto_fit=app_data)

    with dpg.tab(label="Home", tag="main_tab"):
        # The sizes given here are only starting values; on_viewport_resize() sets the real ones.
        with dpg.group(horizontal=True, horizontal_spacing=GAP, tag="main_tab_columns"):

            # ===================== LEFT: valve table =====================
            with dpg.child_window(tag="main_tab_valve_panel", width=350, height=800, border=False):
                with dpg.table(
                    header_row=True,
                    row_background=True,
                    borders_innerH=True,
                    borders_outerH=True,
                    borders_innerV=True,
                    borders_outerV=True,
                    policy=dpg.mvTable_SizingFixedFit,
                    scrollY=True,
                    freeze_rows=1,
                    width=-1,
                    height=-1,
                ):
                    # Buttons/icons keep their natural width; "Location" absorbs whatever space is left
                    dpg.add_table_column(label="#")
                    dpg.add_table_column(label="Location", width_stretch=True)
                    dpg.add_table_column(label="Open")
                    dpg.add_table_column(label="Close")
                    dpg.add_table_column(label="Status")
                    dpg.add_table_column(label="%")

                    for i in range(0, 36):
                        with dpg.table_row():
                            dpg.add_text(str(i))
                            dpg.add_text("Valve " + str(i), tag="valve_loc_" + str(i))
                            dpg.add_button(label="Open", tag=f"valve_open_button_{i}", callback=callback_open_valve, user_data=i)
                            dpg.add_button(label="Close", tag=f"valve_close_button_{i}", callback=callback_close_valve, user_data=i)
                            with dpg.drawlist(45, 20):
                                dpg.draw_rectangle(
                                    (0, 0),
                                    (20, 20),
                                    color=(0, 255, 0, 150),
                                    fill=(0, 255, 0, 150),
                                    tag=f"valve_desired_icon_{i}",
                                )
                                dpg.draw_circle(
                                    (34, 10),
                                    radius=10,
                                    color=(255, 0, 0, 150),
                                    fill=(255, 0, 0, 150),
                                    tag=f"valve_actual_icon_{i}",
                                )
                            dpg.add_text("0%", tag=f"rs485_valve_{i}")

            # ===================== CENTRE: P&ID + console / pyro / sequence =====================
            with dpg.group(tag="main_tab_center_column"):
                with dpg.child_window(tag="main_tab_pnid_panel", width=700, height=700, border=False, no_scrollbar=True):
                    # Build the desired PNID setup (positions are relative to this panel)
                    # pnid_data_tags, pnid_valve_tags, possible_valve_locations, possible_sensor_locations = pnid_setups.build_full_setup()
                    # pnid_data_tags, pnid_valve_tags, possible_valve_locations, possible_sensor_locations = pnid_setups.build_nov_9_hotfire_setup()
                    pnid_data_tags, pnid_valve_tags, possible_valve_locations, possible_sensor_locations = pnid_setups.build_fall_2026_setup()

                with dpg.group(horizontal=True, horizontal_spacing=GAP):
                    # ---- ECU console ----
                    with dpg.child_window(tag="main_tab_ecu_panel", width=450, height=300, border=False):
                        dpg.add_text("ECU Output:")
                        dpg.add_input_text(
                            default_value="{command} \n command",
                            readonly=True,
                            multiline=True,
                            width=-1,
                            height=100,
                            tag="main_tab_ecu_recieved_commands",
                        )
                        dpg.add_text("Send Command to ECU:")
                        with dpg.group(horizontal=True):
                            dpg.add_input_text(
                                default_value="",
                                readonly=False,
                                width=-(65 + GAP),
                                tag="main_tab_ecu_command_input",
                                hint="{x,x}",
                            )
                            dpg.add_button(
                                label="Send",
                                width=65,
                                callback=callback_send_command,
                                user_data="main_tab_ecu_command_input",
                            )
                        dpg.add_input_text(
                            default_value="Sent Command...",
                            readonly=True,
                            multiline=True,
                            width=-1,
                            height=-1,
                            tag="main_tab_ecu_sent_commands",
                        )

                    # ---- Pyro + sequence controls ----
                    with dpg.child_window(tag="main_tab_control_panel", width=CONTROL_COL_W, height=300, border=False):
                        dpg.add_checkbox(label="Arm Pyro Channels", callback=arm_pyro_channels)
                        with dpg.table(
                            header_row=True,
                            row_background=True,
                            borders_innerH=True,
                            borders_outerH=True,
                            borders_innerV=True,
                            borders_outerV=True,
                            policy=dpg.mvTable_SizingStretchProp,
                            width=-1,
                        ):
                            dpg.add_table_column(label="Name", init_width_or_weight=0.3)
                            dpg.add_table_column(label="Fire", init_width_or_weight=0.2)
                            dpg.add_table_column(label="Status", init_width_or_weight=0.25)

                            for i in range(2):
                                with dpg.table_row():
                                    dpg.add_text(f"Pyro {i}")
                                    dpg.add_button(label="Fire", tag=f"pyro_fire_button_{i}", callback=callback_fire_pyro, user_data=i)
                                    with dpg.drawlist(40, 20):
                                        dpg.draw_rectangle(
                                            (10, 0),
                                            (30, 20),
                                            color=(255, 0, 0, 150),
                                            fill=(255, 0, 0, 150),
                                            tag=f"pyro_status_icon_{i}",
                                        )
                        arm_pyro_channels(None, False, None)

                        dpg.add_spacer(height=4)
                        dpg.add_separator()
                        dpg.add_spacer(height=4)

                        dpg.add_button(
                            label="Execute Launch Sequence",
                            width=-1,
                            callback=callback_start_hardcoded_launch_sequence,
                        )  # button for hardcoded sequence
                        dpg.add_text("Run Uploaded Sequence:")
                        dpg.add_combo(["x", "s"], width=-1, tag="main_tab_sequence_select")
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Upload", callback=callback_upload_sequence, user_data="main_tab_sequence_select")
                            dpg.add_button(
                                label="Start",
                                callback=callback_start_sequence,
                                user_data="main_tab_sequence_select",
                                tag="main_tab_sequence_start_button",
                                enabled=False,
                            )
                            dpg.add_button(label="Cancel", callback=sequence_executer.cancel_sequence)
                        with dpg.group(horizontal=True):
                            dpg.add_text("Step:")
                            dpg.add_text("xx/102", tag="main_tab_step_number")
                            dpg.add_text("for 12.1s", tag="main_tab_step_time_left")

            # ===================== RIGHT: plot controls + plots =====================
            with dpg.child_window(tag="main_tab_plot_panel", width=600, height=800, border=False):
                with dpg.group(tag="main_tab_plot_controls"):
                    dpg.add_text("", tag="main_tab_timestamp")

                    with dpg.group(horizontal=True):
                        dpg.add_text("Plot Lookback (s)")
                        dpg.add_input_float(default_value=30, width=100, min_value=1, format="%.1f", tag="main_tab_seconds_lookback")
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="30 sec", callback=set_lookback_value, user_data=30)
                        dpg.add_button(label="1 min", callback=set_lookback_value, user_data=60)
                        dpg.add_button(label="5 min", callback=set_lookback_value, user_data=300)
                        dpg.add_button(label="30 min", callback=set_lookback_value, user_data=1800)
                        dpg.add_button(label="1 hr", callback=set_lookback_value, user_data=3600)

                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(label="Autofit Graphs", default_value=True, callback=set_plot_autofit)
                        dpg.add_checkbox(label="Smoothed Values", default_value=False, tag="smoothed_checkbox")

                    with dpg.group(horizontal=True):
                        dpg.add_text("Samples to average/smooth over:")
                        dpg.add_input_int(default_value=5, width=100, min_value=1, tag="smooth_samples_input")

                with dpg.plot(label="Pressure Transducers & Load Cells", height=300, width=-1, tag="pt_lc_plot"):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis_1", auto_fit=True)
                    dpg.add_plot_axis(dpg.mvYAxis, label="Pressure (psi)", tag="y_axis_psi", auto_fit=True)
                    dpg.add_plot_axis(dpg.mvYAxis2, label="Force (lbs)", tag="y_axis_lbs", auto_fit=True, opposite=True)

                with dpg.plot(label="Thermocouples & Voltages", height=300, width=-1, tag="tc_v_plot"):
                    dpg.add_plot_legend()
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis_2", auto_fit=True)
                    dpg.add_plot_axis(dpg.mvYAxis, label="Temperature (C)", tag="y_axis_c", auto_fit=True)
                    dpg.add_plot_axis(dpg.mvYAxis2, label="Voltage (V)", tag="y_axis_v", auto_fit=True, opposite=True)