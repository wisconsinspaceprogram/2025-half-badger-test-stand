import dearpygui.dearpygui as dpg
from pathlib import Path
from core import T7_Pro_poller

save_config_data = ""


def get_sensor_type_list():
    # Callback to core logic to get programmed sensor types
    return ["Pressure Transducer", "Thermocouple Type T", "Thermocouple Type K", "Load Cell", "Voltage"]


def get_physical_sensor_locations():
    return [
        "-",
        "LOX Tank Top",
        "LOX Tank Bottom",
        "LOX Venturi",
        "LOX Manifold",
        "IPA Manifold",
        "IPA Tank Bottom",
        "IPA Tank Top",
        "Combustion Chamber",
        "Custom",
    ]


def get_sensor_type(channel: int):
    dpg.get_value("type_T7p_" + str(channel))


# def get_unit_from_type(type: str):
#   unit = ''
#   match type:
#     case "Pressure Transducer":
#       unit = 'psi'
#     case "Thermocouple Type T" | "Thermocouple Type K":
#       unit = 'C'
#     case "Load Cell":
#       unit = 'lbs'
#     case "Voltage":
#       unit = 'V'
#     case _:
#       unit = ''
#   return unit

# def get_unit(daq: str, channel: int):
#   return get_unit_from_type(daq, channel)


def custom_location_combo_callback(sender, app_data, user_data):
    if app_data == "Custom":
        dpg.configure_item(user_data, show=True)
    else:
        dpg.configure_item(user_data, show=False)


def show_mapping_callback(sender, app_data, user_data):
    if app_data == "Pressure Transducer" or app_data == "Load Cell":

        for item in user_data:
            dpg.configure_item(item, show=True)
    else:
        for item in user_data:
            dpg.configure_item(item, show=False)


def callback_enable(sender, app_data, user_data):
    for item in user_data:
        dpg.configure_item(item, show=app_data)

    show_mapping_callback(
        None,
        dpg.get_value(sender.replace("enabled", "type")),
        [
            sender.replace("enabled", "v_min"),
            sender.replace("enabled", "v_max"),
            sender.replace("enabled", "out_min"),
            sender.replace("enabled", "out_max"),
        ],
    )
    custom_location_combo_callback(None, dpg.get_value(sender.replace("enabled", "sensor_loc_combo")), sender.replace("enabled", "custom_loc"))

    if not app_data:
        for item in [
            sender.replace("enabled", "v_min"),
            sender.replace("enabled", "v_max"),
            sender.replace("enabled", "out_min"),
            sender.replace("enabled", "out_max"),
        ]:
            dpg.configure_item(item, show=False)
        dpg.configure_item(sender.replace("enabled", "custom_loc"), show=False)


def send_config_data(sender, app_data, user_data):
    active_channels = []
    active_channel_types = []
    sensor_locations = []
    mappings = []

    for i in range(14):
        row_string = "T7p_CH" + str(i + 1)

        enabled = dpg.get_value(f"enabled_{row_string}")
        if enabled:
            active_channels.append(i + 1)
            active_channel_types.append(dpg.get_value(f"type_{row_string}"))

            location_input_combo = dpg.get_value("sensor_loc_combo_" + row_string)

            if location_input_combo == "-":
                sensor_locations.append(row_string)
            elif location_input_combo == "Custom":
                sensor_locations.append(dpg.get_value(f"custom_loc_{row_string}"))
            else:
                sensor_locations.append(location_input_combo)

            mappings.append(
                (
                    (dpg.get_value("v_min_" + row_string), dpg.get_value("v_max_" + row_string)),
                    (dpg.get_value("out_min_" + row_string), dpg.get_value("out_max_" + row_string)),
                )
            )

        scan_rate = dpg.get_value("T7p_scan_rate_input")

    T7_Pro_poller.update_config(active_channels, active_channel_types, mappings, sensor_locations, scan_rate)


def generate_channel_config_string(channel: int):
    row_string = "T7p_CH" + str(channel)
    enabled = dpg.get_value(f"enabled_{row_string}")
    type = dpg.get_value(f"type_{row_string}")
    location_input_combo = dpg.get_value("sensor_loc_combo_" + row_string)
    custom_loc = dpg.get_value(f"custom_loc_{row_string}")
    v_min_value = dpg.get_value("v_min_" + row_string)
    v_max_value = dpg.get_value("v_max_" + row_string)
    out_min_value = dpg.get_value("out_min_" + row_string)
    out_max_value = dpg.get_value("out_max_" + row_string)

    out_string = f"{enabled},{type},{location_input_combo},{custom_loc},{v_min_value},{v_max_value},{out_min_value},{out_max_value}"

    return out_string


def callback_save_config():

    global save_config_data

    save_config_data = str(dpg.get_value("T7p_scan_rate_input")) + "\n"

    for i in range(14):
        save_config_data += generate_channel_config_string(i + 1)
        if i != 13:
            save_config_data += "\n"

    dpg.show_item("T7p_save_dialog")


def callback_save_config_confirm(sender, app_data, user_data):
    path = app_data["file_path_name"]
    try:
        with open(path, "w") as file:
            file.write(save_config_data)
        # print(f"Saved to {path}")
    except Exception as e:
        print(f"Failed to save file: {e}")


def callback_open_config():
    dpg.show_item("T7p_open_dialog")


def callback_open_config_confirm(sender, app_data, user_data):
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
                dpg.set_value("T7p_scan_rate_input", float(info[0]))
            else:
                row_string = "T7p_CH" + str(i_line)

                dpg.set_value(f"enabled_{row_string}", info[0] == "True")
                dpg.set_value(f"type_{row_string}", info[1])
                dpg.set_value("sensor_loc_combo_" + row_string, info[2])
                dpg.set_value(f"custom_loc_{row_string}", info[3])
                dpg.set_value("v_min_" + row_string, float(info[4]))
                dpg.set_value("v_max_" + row_string, float(info[5]))
                dpg.set_value("out_min_" + row_string, float(info[6]))
                dpg.set_value("out_max_" + row_string, float(info[7]))

                custom_location_combo_callback(None, dpg.get_value("sensor_loc_combo_" + row_string), f"custom_loc_{row_string}")
                show_mapping_callback(
                    None, f"type_{row_string}", ["v_min_" + row_string, "v_max_" + row_string, "out_min_" + row_string, "out_max_" + row_string]
                )
                callback_enable(
                    f"enabled_{row_string}",
                    dpg.get_value(f"enabled_{row_string}"),
                    ["custom_loc_" + row_string, "sensor_loc_combo_" + row_string, "type_" + row_string, "id_" + row_string]
                    + ["v_min_" + row_string, "v_max_" + row_string, "out_min_" + row_string, "out_max_" + row_string],
                )
    except Exception as e:
        print(e)


def load_defaults():
    this_file_dir = Path(__file__).parent
    file_path = this_file_dir.parent / "save_files" / "defaults" / "default_T7_Pro.csv"
    callback_open_config_confirm(None, {"file_path_name": file_path}, None)
    send_config_data(None, None, None)


def build():
    with dpg.collapsing_header(label="T7 Pro DAQ", default_open=True):
        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_save_config_confirm,
            id="T7p_save_dialog",
            modal=True,
            width=500,
            height=400,
            label="Save T7 Pro Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_open_config_confirm,
            id="T7p_open_dialog",
            modal=True,
            width=500,
            height=400,
            label="Load T7 Pro Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.group(horizontal=True):
            dpg.add_button(label="Apply To DAQ and Clear", callback=send_config_data, tag="T7p_apply")
            with dpg.tooltip("T7p_apply"):
                dpg.add_text(
                    default_value="Update the current DAQ settings with the below configurations. Note this will clear the data in the home page quick view. A new save file will be started"
                )
            # dpg.add_button(label="Clear")
            dpg.add_button(label="Open From File", callback=callback_open_config)
            dpg.add_button(label="Save To File", callback=callback_save_config)
        with dpg.group(horizontal=True):
            dpg.add_text("Scan Rate: ")
            dpg.add_input_int(default_value=5, width=150, tag="T7p_scan_rate_input")
            dpg.add_text("Hz")
        with dpg.table(header_row=True, row_background=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):

            dpg.add_table_column(label="Enable?", init_width_or_weight=0.15)
            dpg.add_table_column(label="Channel", init_width_or_weight=0.5)
            dpg.add_table_column(label="ID", init_width_or_weight=0.5)
            dpg.add_table_column(label="Location", init_width_or_weight=1)
            dpg.add_table_column(label="Type", init_width_or_weight=0.75)
            dpg.add_table_column(label="Voltage Mapping", init_width_or_weight=1)
            dpg.add_table_column(label="Reading", init_width_or_weight=0.5)

            for i in range(0, 14):
                with dpg.table_row():

                    row_string = "T7p_CH" + str(i + 1)

                    # ===
                    dpg.add_text(str(i + 1), tag="channel_" + row_string)
                    # ===
                    dpg.add_text(row_string, tag="id_" + row_string)
                    # ===
                    with dpg.group(horizontal=True):
                        custom_input = dpg.add_input_text(label="", hint="Custom Location", show=False, tag="custom_loc_" + row_string)
                        location_combo = dpg.add_combo(
                            get_physical_sensor_locations(),
                            default_value="-",
                            callback=custom_location_combo_callback,
                            user_data=custom_input,
                            tag="sensor_loc_combo_" + row_string,
                        )
                        custom_location_combo_callback(None, dpg.get_value(location_combo), custom_input)
                        dpg.move_item(location_combo, before=custom_input)
                    # ===

                    with dpg.group(horizontal=True) as mapping_group:
                        dpg.add_drag_float(label="V to", width=50, default_value=0.0, show=False, tag="v_min_" + row_string)
                        dpg.add_drag_float(label="V => ", width=50, default_value=10.0, show=False, tag="v_max_" + row_string)

                        dpg.add_drag_float(label=" to", width=50, default_value=0.0, show=False, tag="out_min_" + row_string)
                        dpg.add_drag_float(label="", width=50, default_value=1000, show=False, tag="out_max_" + row_string)

                    list_of_mapping_items = ["v_min_" + row_string, "v_max_" + row_string, "out_min_" + row_string, "out_max_" + row_string]
                    type_combo = dpg.add_combo(
                        get_sensor_type_list(),
                        default_value="Voltage",
                        tag="type_" + row_string,
                        callback=show_mapping_callback,
                        user_data=list_of_mapping_items,
                    )

                    dpg.move_item(type_combo, before=mapping_group)
                    # ===
                    list_of_items_to_hide = [
                        "custom_loc_" + row_string,
                        "sensor_loc_combo_" + row_string,
                        "type_" + row_string,
                        "id_" + row_string,
                    ] + list_of_mapping_items
                    dpg.add_checkbox(
                        default_value=True,
                        tag="enabled_" + row_string,
                        before="channel_" + row_string,
                        callback=callback_enable,
                        user_data=list_of_items_to_hide,
                    )

                    callback_enable("enabled_" + row_string, dpg.get_value("enabled_" + row_string), list_of_items_to_hide)

                    dpg.add_text("0.0", tag="reading_" + row_string)
