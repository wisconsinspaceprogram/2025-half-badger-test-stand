import dearpygui.dearpygui as dpg
from pathlib import Path
from core import ECU_Poller
from gui import main_tab

save_config_data = ""


def custom_location_combo_callback(sender, app_data, user_data):
    if app_data == "Custom":
        dpg.configure_item(user_data, show=True)
    else:
        dpg.configure_item(user_data, show=False)


def callback_enable(sender, app_data, user_data):
    for item in user_data:
        dpg.configure_item(item, show=app_data)

    if app_data:
        custom_tag = user_data[0]
        combo_tag = user_data[1]
        custom_location_combo_callback(None, dpg.get_value(combo_tag), custom_tag)


def send_config_data(sender, app_data, user_data):
    pt_enabled = []
    pt_locations = []
    pt_mappings = []
    tc_enabled = []
    tc_locations = []

    for i in range(4):
        row_string = f"ECU_PT{i+1}"
        enabled = dpg.get_value(f"enabled_{row_string}")
        pt_enabled.append(enabled)

        location_input_combo = dpg.get_value("sensor_loc_combo_" + row_string)
        if location_input_combo == "-":
            pt_locations.append(row_string)
        elif location_input_combo == "Custom":
            pt_locations.append(dpg.get_value(f"custom_loc_{row_string}"))
        else:
            pt_locations.append(location_input_combo)

        pt_mappings.append(
            (
                (dpg.get_value("map_in_min_" + row_string), dpg.get_value("map_in_max_" + row_string)),
                (dpg.get_value("map_out_min_" + row_string), dpg.get_value("map_out_max_" + row_string)),
            )
        )

    for i in range(4):
        row_string = f"ECU_TC{i+1}"
        enabled = dpg.get_value(f"enabled_{row_string}")
        tc_enabled.append(enabled)

        location_input_combo = dpg.get_value("sensor_loc_combo_" + row_string)
        if location_input_combo == "-":
            tc_locations.append(row_string)
        elif location_input_combo == "Custom":
            tc_locations.append(dpg.get_value(f"custom_loc_{row_string}"))
        else:
            tc_locations.append(location_input_combo)

    ECU_Poller.update_ecu_sensor_config(pt_enabled, pt_locations, tc_enabled, tc_locations, pt_mappings=pt_mappings)


def generate_channel_config_string(row_string: str, sensor_kind: str):
    enabled = dpg.get_value(f"enabled_{row_string}")
    location_input_combo = dpg.get_value("sensor_loc_combo_" + row_string)
    custom_loc = dpg.get_value(f"custom_loc_{row_string}")

    out_values = [sensor_kind, row_string, str(enabled), location_input_combo, custom_loc]

    if sensor_kind == "PT":
        out_values.extend(
            [
                str(dpg.get_value("map_in_min_" + row_string)),
                str(dpg.get_value("map_in_max_" + row_string)),
                str(dpg.get_value("map_out_min_" + row_string)),
                str(dpg.get_value("map_out_max_" + row_string)),
            ]
        )

    return ",".join(out_values)


def callback_save_config():
    global save_config_data

    lines = []
    for i in range(4):
        lines.append(generate_channel_config_string(f"ECU_PT{i+1}", "PT"))
    for i in range(4):
        lines.append(generate_channel_config_string(f"ECU_TC{i+1}", "TC"))

    save_config_data = "\n".join(lines)
    dpg.show_item("ECU_sensor_save_dialog")


def callback_save_config_confirm(sender, app_data, user_data):
    path = app_data["file_path_name"]
    try:
        with open(path, "w") as file:
            file.write(save_config_data)
    except Exception as e:
        print(f"Failed to save file: {e}")


def callback_open_config():
    dpg.show_item("ECU_sensor_open_dialog")


def callback_open_config_confirm(sender, app_data, user_data):
    try:
        load_file(Path(app_data["file_path_name"]))
    except Exception as e:
        print(f"Failed to open file: {e}")


def load_file(file_path: Path):
    try:
        with open(file_path, "r") as file:
            raw_csv_lines = [line.strip() for line in file.readlines() if line.strip() != ""]

        for line in raw_csv_lines:
            info = line.split(",")
            if len(info) < 4:
                continue

            sensor_kind = info[0].strip().upper()
            row_string = info[1].strip()
            enabled = info[2].strip().lower() == "true"
            location_choice = info[3].strip()
            custom_value = info[4].strip() if len(info) > 4 else row_string

            if sensor_kind not in ("PT", "TC"):
                continue
            if not row_string.startswith(f"ECU_{sensor_kind}"):
                continue

            dpg.set_value(f"enabled_{row_string}", enabled)
            dpg.set_value("sensor_loc_combo_" + row_string, location_choice)
            dpg.set_value(f"custom_loc_{row_string}", custom_value)

            if sensor_kind == "PT" and len(info) >= 9:
                dpg.set_value("map_in_min_" + row_string, float(info[5]))
                dpg.set_value("map_in_max_" + row_string, float(info[6]))
                dpg.set_value("map_out_min_" + row_string, float(info[7]))
                dpg.set_value("map_out_max_" + row_string, float(info[8]))

            items_to_toggle = ["custom_loc_" + row_string, "sensor_loc_combo_" + row_string]
            if sensor_kind == "PT":
                items_to_toggle.extend(
                    [
                        "map_in_min_" + row_string,
                        "map_in_max_" + row_string,
                        "map_out_min_" + row_string,
                        "map_out_max_" + row_string,
                    ]
                )

            callback_enable(None, enabled, items_to_toggle)
            custom_location_combo_callback(None, dpg.get_value("sensor_loc_combo_" + row_string), f"custom_loc_{row_string}")

    except Exception as e:
        print(f"Failed to load ECU sensor defaults: {e}")


def load_defaults():
    this_file_dir = Path(__file__).parent
    file_path = this_file_dir.parent / "save_files" / "defaults" / "default_ECU_sensors.csv"

    load_file(file_path)
    send_config_data(None, None, None)


def _build_sensor_row(row_string: str, label: str, sensor_type: str, with_mapping: bool):
    with dpg.table_row():
        toggle_items = ["custom_loc_" + row_string, "sensor_loc_combo_" + row_string]
        if with_mapping:
            toggle_items.extend(
                [
                    "map_in_min_" + row_string,
                    "map_in_max_" + row_string,
                    "map_out_min_" + row_string,
                    "map_out_max_" + row_string,
                ]
            )

        dpg.add_checkbox(
            default_value=True,
            callback=callback_enable,
            user_data=toggle_items,
            tag="enabled_" + row_string,
        )

        dpg.add_text(label)
        dpg.add_text(sensor_type)

        with dpg.group(horizontal=True):
            custom_input = dpg.add_input_text(
                default_value=label,
                width=250,
                show=False,
                tag="custom_loc_" + row_string,
            )
            location_combo = dpg.add_combo(
                main_tab.get_possible_sensor_locations() + ["Custom", "-"],
                callback=custom_location_combo_callback,
                user_data=custom_input,
                width=250,
                default_value=label,
                tag="sensor_loc_combo_" + row_string,
            )
            custom_location_combo_callback(None, dpg.get_value(location_combo), custom_input)
            dpg.move_item(location_combo, before=custom_input)

        if with_mapping:
            with dpg.group(horizontal=True):
                dpg.add_drag_float(label="V to", width=60, default_value=0.0, tag="map_in_min_" + row_string)
                dpg.add_drag_float(label="V =>", width=60, default_value=5.0, tag="map_in_max_" + row_string)
                dpg.add_drag_float(label="to", width=60, default_value=0.0, tag="map_out_min_" + row_string)
                dpg.add_drag_float(label="", width=60, default_value=1000.0, tag="map_out_max_" + row_string)
        else:
            dpg.add_text("-")

        dpg.add_text("0.0", tag="reading_" + row_string)


def build():
    with dpg.collapsing_header(label="ECU Sensor Config", default_open=True):
        dpg.add_text("Enable and name ECU PT and TC sensors for plotting")

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_save_config_confirm,
            id="ECU_sensor_save_dialog",
            modal=True,
            width=500,
            height=400,
            label="Save ECU Sensor Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_open_config_confirm,
            id="ECU_sensor_open_dialog",
            modal=True,
            width=500,
            height=400,
            label="Load ECU Sensor Config",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.group(horizontal=True):
            dpg.add_button(label="Apply To DAQ and Clear", callback=send_config_data, tag="ECU_sensor_apply")
            dpg.add_button(label="Open From File", callback=callback_open_config)
            dpg.add_button(label="Save To File", callback=callback_save_config)

        with dpg.table(header_row=True, row_background=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):
            dpg.add_table_column(label="Enable?", init_width_or_weight=0.15)
            dpg.add_table_column(label="Channel", init_width_or_weight=0.4)
            dpg.add_table_column(label="Type", init_width_or_weight=0.4)
            dpg.add_table_column(label="Location", init_width_or_weight=1.0)
            dpg.add_table_column(label="Mapping", init_width_or_weight=1.2)
            dpg.add_table_column(label="Reading", init_width_or_weight=0.5)

            for i in range(4):
                _build_sensor_row(f"ECU_PT{i+1}", f"ECU PT{i+1}", "Pressure Transducer", with_mapping=True)

            for i in range(4):
                _build_sensor_row(f"ECU_TC{i+1}", f"ECU TC{i+1}", "Thermocouple Type K", with_mapping=False)
