import dearpygui.dearpygui as dpg
from pathlib import Path
from core import ECU_Poller

valve_locations = [
    "GN2 Main",
    "LOX Purge",
    "IPA Purge",
    "LOX Tank Vent",
    "LOX Fill",
    "LOX Fill Vent",
    "LOX Venturi Iso",
    "LOX Venturi Vent",
    "LOX Main",
    "IPA Tank Vent",
    "IPA Fill Dump",
    "IPA Main",
    "Not Connected",
    "Custom",
]
valve_save_data = ""


def custom_location_combo_callback(sender, app_data, user_data):
    if app_data == "Custom":
        dpg.configure_item(user_data, show=True)
    else:
        dpg.configure_item(user_data, show=False)


def send_config_data(sender, app_data, user_data):
    new_locs = []
    for i in range(24):
        location = dpg.get_value(f"valve_loc_combo_{i}")

        if location == "Not Connected":
            location = f"Valve_{i}"

        if location == "Custom":
            location = dpg.get_value(f"custom_loc_valve_{i}")

        new_locs.append(location)

    ECU_Poller.update_valve_locations(new_locs)
    ECU_Poller.update_port_settings(dpg.get_value("ecu_port_input"), int(dpg.get_value("ecu_baud_input")))


def generate_channel_valve_string(channel_index: int):
    return f'{channel_index},{dpg.get_value(f"valve_loc_combo_{channel_index}")},{dpg.get_value(f"custom_loc_valve_{channel_index}")}'


def callback_save_config():

    global valve_save_data

    valve_save_data = f"{dpg.get_value('ecu_port_input')},{dpg.get_value('ecu_baud_input')}\n"

    for i in range(24):
        valve_save_data += generate_channel_valve_string(i)
        if i != 23:
            valve_save_data += "\n"

    dpg.show_item("valve_save_dialog")


def callback_save_valve_confirm(sender, app_data, user_data):
    path = app_data["file_path_name"]
    try:
        with open(path, "w") as file:
            file.write(valve_save_data)
        # print(f"Saved to {path}")
    except Exception as e:
        print(f"Failed to save file: {e}")


def callback_open_config():
    dpg.show_item("valve_open_dialog")


def callback_open_valve_confirm(sender, app_data, user_data):
    try:
        path = app_data["file_path_name"]
        raw_csv_lines = []
        csv_lines = []

        with open(path, "r") as file:
            raw_csv_lines = file.readlines()
        # print("Loaded lines:")
        for line in raw_csv_lines:
            csv_lines.append(line.strip())

        for i_line in range(len(csv_lines)):
            line = csv_lines[i_line]
            info = line.split(",")

            if i_line == 0:
                dpg.set_value("ecu_port_input", info[0])
                dpg.set_value("ecu_baud_input", int(info[1]))
            else:
                dpg.set_value(f"valve_loc_combo_{i_line-1}", info[1])
                dpg.set_value(f"custom_loc_valve_{i_line-1}", info[1])
                print(i_line)

                custom_location_combo_callback(None, info[1], f"custom_loc_valve_{i_line-1}")
    except Exception as e:
        print("Open valve config erorr:", e)


def load_defaults():
    this_file_dir = Path(__file__).parent
    file_path = this_file_dir.parent / "save_files" / "defaults" / "default_valve.csv"
    callback_open_valve_confirm(None, {"file_path_name": file_path}, None)
    send_config_data(None, None, None)


def build():
    with dpg.tab(label="Valve Config", tag="valve_config_tab"):

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_save_valve_confirm,
            id="valve_save_dialog",
            modal=True,
            width=500,
            height=400,
            label="Save Valve Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_open_valve_confirm,
            id="valve_open_dialog",
            modal=True,
            width=500,
            height=400,
            label="Load Valve Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.group(horizontal=True):
            dpg.add_button(label="Apply", callback=send_config_data, user_data=None)
            dpg.add_button(label="Open From File", callback=callback_open_config)
            dpg.add_button(label="Save To File", callback=callback_save_config)

        with dpg.group(horizontal=True):
            dpg.add_input_text(default_value="COM7", width=100, tag="ecu_port_input")
            dpg.add_input_int(default_value=115200, width=150, tag="ecu_baud_input")

        with dpg.table(header_row=True, row_background=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):

            dpg.add_table_column(label="ECU Channel #", init_width_or_weight=0.2)
            dpg.add_table_column(label="Valve Location", init_width_or_weight=0.2)
            dpg.add_table_column(label="Curretn State", init_width_or_weight=0.2)

            for i in range(24):
                with dpg.table_row():
                    # dpg.add_checkbox()
                    dpg.add_text(str(i))
                    with dpg.group(horizontal=True):
                        custom_input = dpg.add_input_text(label="", hint="Custom Location", show=False, tag=f"custom_loc_valve_{i}")
                        location_combo = dpg.add_combo(
                            valve_locations,
                            default_value="Not Connected",
                            callback=custom_location_combo_callback,
                            user_data=custom_input,
                            tag=f"valve_loc_combo_{i}",
                        )
                        custom_location_combo_callback(None, dpg.get_value(location_combo), custom_input)
                        dpg.move_item(location_combo, before=custom_input)
                    dpg.add_text("Open")
