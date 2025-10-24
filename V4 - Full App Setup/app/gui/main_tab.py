import dearpygui.dearpygui as dpg
from pathlib import Path
from core import ECU_Poller, sequence_executer
from gui import pnid_setups

pnid_data_tags = []
pnid_valve_tags = []


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
    index = sequence_executer.get_names().index(dpg.get_value(user_data))
    sequence_executer.run_sequence(index)


def callback_stop_sequence():
    sequence_executer.cancel_sequence()


def make_data_stack(location: str, start: tuple, offset: tuple, count: int, up: bool):
    global pnid_data_tags

    for i in range(count):
        tag = f"PNID_{location.lower()}_data_{i}"
        dpg.add_text(
            default_value="22.1c",
            tag=tag,
            pos=((offset[0] + start[0], offset[1] + start[1] + 10 * (-i if up else i))),
            show=True,
        )
        pnid_data_tags.append(tag)


def make_pnid_valve_icons(location: str, start: tuple, offset: tuple):
    global pnid_valve_tags

    tag = f"PNID_{location.lower()}_valve"
    with dpg.group(pos=(offset[0] + start[0], offset[1] + start[1])):
        with dpg.drawlist(25, 25):
            dpg.draw_rectangle((0, 0), (25, 25), color=(0, 255, 0, 255), fill=(0, 255, 0, 200), tag=tag + "_desired")
            dpg.draw_circle((12.5, 12.5), radius=11, color=(255, 0, 0, 255), fill=(255, 0, 0, 200), tag=tag + "_actual")


def build():
    global pnid_data_tags, pnid_valve_tags

    with dpg.tab(label="Home", tag="main_tab"):

        # Build the desired PNID setup
        pnid_data_tags, pnid_valve_tags = pnid_setups.build_full_setup()

        with dpg.group(pos=(25, 50)):
            with dpg.table(
                header_row=True,
                row_background=True,
                borders_innerH=True,
                borders_outerH=True,
                borders_innerV=True,
                borders_outerV=True,
                width=300,
            ):
                dpg.add_table_column(label="#", init_width_or_weight=0.1)
                dpg.add_table_column(label="Location", init_width_or_weight=0.6)
                dpg.add_table_column(label="Open", init_width_or_weight=0.2)
                dpg.add_table_column(label="Close", init_width_or_weight=0.2)
                dpg.add_table_column(label="Status", init_width_or_weight=0.2)

                for i in range(0, 24):
                    with dpg.table_row():
                        dpg.add_text(str(i))
                        dpg.add_text("Valve " + str(i), tag="valve_loc_" + str(i))
                        dpg.add_button(label="Open", tag=f"valve_open_button_{i}", callback=callback_open_valve, user_data=i)
                        dpg.add_button(label="Close", tag=f"valve_close_button_{i}", callback=callback_close_valve, user_data=i)
                        with dpg.drawlist(60, 20):
                            dpg.draw_rectangle(
                                (0, 0),
                                (20, 20),
                                color=(0, 255, 0, 150),
                                fill=(0, 255, 0, 150),
                                tag=f"valve_desired_icon_{i}",
                            )
                            dpg.draw_circle(
                                (35, 10),
                                radius=10,
                                color=(255, 0, 0, 150),
                                fill=(255, 0, 0, 150),
                                tag=f"valve_actual_icon_{i}",
                            )

        def set_lookback_value(sender, app_data, user_data):
            dpg.set_value("main_tab_seconds_lookback", user_data)

        def set_plot_autofit(sender, app_data, user_data):
            dpg.configure_item("x_axis_1", auto_fit=app_data)
            dpg.configure_item("y_axis_psi", auto_fit=app_data)
            dpg.configure_item("y_axis_lbs", auto_fit=app_data)
            dpg.configure_item("x_axis_2", auto_fit=app_data)
            dpg.configure_item("y_axis_c", auto_fit=app_data)
            dpg.configure_item("y_axis_v", auto_fit=app_data)

        with dpg.group(pos=(1250, 50)):
            with dpg.group(horizontal=True):
                dpg.add_text("Plot Lookback (s)")
                dpg.add_input_float(default_value=30, width=100, min_value=1, format="%.1f", tag="main_tab_seconds_lookback")
                dpg.add_button(label="30 sec", callback=set_lookback_value, user_data=30)
                dpg.add_button(label="1 min", callback=set_lookback_value, user_data=60)
                dpg.add_button(label="5 min", callback=set_lookback_value, user_data=300)
                dpg.add_button(label="30 min", callback=set_lookback_value, user_data=1800)
                dpg.add_button(label="1 hr", callback=set_lookback_value, user_data=3600)

            dpg.add_checkbox(label="Autofit Graphs", default_value=True, callback=set_plot_autofit)

        with dpg.plot(label="Pressure Transducers & Load Cells", height=300, width=600, tag="pt_lc_plot", pos=(1250, 100)):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis_1", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="Pressure (psi)", tag="y_axis_psi", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis2, label="Force (lbs)", tag="y_axis_lbs", auto_fit=True, opposite=True)

        with dpg.plot(label="Thermocouples & Voltages", height=300, width=600, tag="tc_v_plot", pos=(1250, 400)):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="x_axis_2", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis, label="Temperature (C)", tag="y_axis_c", auto_fit=True)
            dpg.add_plot_axis(dpg.mvYAxis2, label="Voltage (V)", tag="y_axis_v", auto_fit=True, opposite=True)

        with dpg.group(pos=(25, 700)):
            with dpg.table(
                header_row=True,
                row_background=True,
                borders_innerH=True,
                borders_outerH=True,
                borders_innerV=True,
                borders_outerV=True,
                width=150,
            ):
                dpg.add_table_column(label="Name", init_width_or_weight=0.3)
                dpg.add_table_column(label="Fire", init_width_or_weight=0.2)
                dpg.add_table_column(label="Status", init_width_or_weight=0.25)

                for i in range(2):
                    with dpg.table_row():
                        dpg.add_text(f"Pyro {i}")
                        dpg.add_button(label="Fire", tag=f"pyro_fire_button_{i}", callback=callback_fire_pyro, user_data=i)
                        with dpg.drawlist(60, 20):
                            dpg.draw_rectangle(
                                (10, 0),
                                (30, 20),
                                color=(255, 0, 0, 150),
                                fill=(255, 0, 0, 150),
                                tag=f"pyro_status_icon_{i}",
                            )

        dpg.add_checkbox(label="Arm Pyro Channels", pos=(25, 675), callback=arm_pyro_channels)
        arm_pyro_channels(None, False, None)

        with dpg.group():
            dpg.add_text(default_value="ECU Output:", pos=(375, 675))
            dpg.add_input_text(
                default_value="{command} \n command",
                pos=(375, 695),
                readonly=True,
                multiline=True,
                width=450,
                height=100,
                tag="main_tab_ecu_recieved_commands",
            )
            dpg.add_text(default_value="Send Command to ECU:", pos=(375, 810))
            dpg.add_input_text(
                default_value="",
                pos=(375, 830),
                readonly=False,
                width=275,
                height=20,
                tag="main_tab_ecu_command_input",
                hint="{x,x}",
            )
            dpg.add_button(
                label="Send",
                pos=(660, 830),
                width=65,
                height=20,
                callback=callback_send_command,
                user_data="main_tab_ecu_command_input",
            )

            dpg.add_input_text(
                default_value="Sent Command...",
                pos=(375, 855),
                readonly=True,
                multiline=True,
                width=450,
                height=100,
                tag="main_tab_ecu_sent_commands",
            )

            # dpg.add_text(default_value="Battery Voltage:", pos=(25, 475))
            # dpg.add_text(default_value="7.7", pos=(150, 475), color=(255, 100, 100, 255))

        with dpg.group(pos=(25, 815)):
            dpg.add_text("Run Sequence:")
            dpg.add_combo(["x", "s"], width=250, tag="main_tab_sequence_select")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Start", callback=callback_start_sequence, user_data="main_tab_sequence_select")
                dpg.add_button(label="Cancel", callback=sequence_executer.cancel_sequence)
                dpg.add_text("xx/102", tag="main_tab_step_number")
                dpg.add_text("for 12.1s", tag="main_tab_step_time_left")
