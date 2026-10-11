import math
import threading
import dearpygui.dearpygui as dpg
import time
from core import T7_poller, T7_Pro_poller, U6_Pro_poller, ECU_Poller, sequence_executer, utils
from gui import main_tab

startTime = time.time()


def sigfig_round(x, sig):
    try:
        return round(x, sig - int(math.floor(math.log10(abs(float(x))))) - 1)
    except:
        return -1


def update_thread():

    last_main_plot_update = startTime
    last_main_ecu_update = startTime
    last_sensor_config_update = startTime

    main_thread = threading.main_thread()
    while main_thread.is_alive():

        cur_time = time.time()
        if dpg.get_value("main_tab"):
            # Update timestamp every loop, show milliseconds
            dpg.set_value("main_tab_timestamp", time.strftime("%Y-%m-%d %H:%M:%S.") + f"{int((cur_time % 1) * 1000):03d}")
            # Update main plot every 0.1 seconds
            if cur_time - last_main_plot_update > 0.1:
                last_main_plot_update = cur_time

                # T7 Updater
                active_channels = T7_poller.get_active_channels()
                acctive_channel_locations = T7_poller.get_sensor_locations()

                pnid_data_tags = main_tab.get_pnid_data_tags()
                used_pnid_data_tags = []

                # Smoothing Fun
                smoothed_boolean = dpg.get_value("smoothed_checkbox")
                smooth_length = abs(dpg.get_value("smooth_samples_input"))
                if smooth_length == 0:
                    smooth_length = 1

                for i in range(len(active_channels)):
                    channel = active_channels[i]

                    channel_unit = T7_poller.get_unit(channel)
                    correct_axis = f"y_axis_{str.lower(channel_unit)}"
                    series_tag = f"T7_CH{channel}_main_plot"

                    # Seeing if item is already plotted
                    if dpg.does_item_exist(series_tag):
                        # If exists, let's check it's parent axis
                        if correct_axis != dpg.get_item_alias(dpg.get_item_parent(series_tag)):
                            dpg.delete_item(series_tag)
                            dpg.add_line_series(
                                [],
                                [],
                                label=f"T7_CH{channel}",
                                parent=correct_axis,
                                tag=series_tag,
                                show=True,
                            )
                    else:
                        dpg.add_line_series(
                            [],
                            [],
                            label=f"T7_CH{channel}",
                            parent=correct_axis,
                            tag=series_tag,
                            show=True,
                        )

                    raw_data = T7_poller.get_data(max(dpg.get_value("main_tab_seconds_lookback"), 1), channel)

                    # here for smooth
                    smooth_y = []
                    if smoothed_boolean:
                        smooth_y = utils.smooth_list(raw_data[1], smooth_length)
                    else:
                        smooth_y = raw_data[1]

                    data = (raw_data[0], smooth_y)

                    dpg.set_value(series_tag, data)
                    dpg.configure_item(series_tag, label=acctive_channel_locations[i])

                    # Setting the data displays on the PNID
                    if len(data[1]) > 0:
                        found = False
                        for tag in pnid_data_tags:
                            # removing the PNID_ prefix on the data label tag
                            trimmed = tag[5:]

                            # if the location prefix matches the data location, and has not been used, data tags have _x suffix
                            if trimmed.startswith(acctive_channel_locations[i].lower()) and not tag in used_pnid_data_tags:
                                used_pnid_data_tags.append(tag)
                                dpg.set_value(tag, str(sigfig_round(data[1][0], 3)) + channel_unit)
                                found = True
                                break

                        if not found:
                            for tag in pnid_data_tags:
                                trimmed = tag[5:]
                                # if the location is custom, we'll just find the first custom location tag to put in it in
                                # and label the respective location with text
                                if trimmed.startswith("custom") and not tag in used_pnid_data_tags:
                                    used_pnid_data_tags.append(tag)
                                    dpg.set_value(
                                        tag,
                                        acctive_channel_locations[i] + ": " + str(sigfig_round(data[1][0], 3)) + channel_unit,
                                    )
                                    found = True
                                    break

                for tag in pnid_data_tags:
                    if tag in used_pnid_data_tags:
                        dpg.show_item(tag)
                    else:
                        dpg.hide_item(tag)

                # Deleting any disabled channels from the plots
                for i in range(36):
                    if not ((i + 1) in active_channels) and dpg.does_item_exist(f"T7_CH{i+1}_main_plot"):
                        dpg.delete_item(f"T7_CH{i+1}_main_plot")

                # T7 Pro Updater
                active_channels = T7_Pro_poller.get_active_channels()
                acctive_channel_locations = T7_Pro_poller.get_sensor_locations()

                # pnid_data_tags = main_tab.get_pnid_data_tags()
                # used_pnid_data_tags = []
                for i in range(len(active_channels)):
                    channel = active_channels[i]

                    channel_unit = T7_Pro_poller.get_unit(channel)
                    correct_axis = f"y_axis_{str.lower(channel_unit)}"
                    series_tag = f"T7p_CH{channel}_main_plot"

                    # Seeing if item is already plotted
                    if dpg.does_item_exist(series_tag):
                        # If exists, let's check it's parent axis
                        if correct_axis != dpg.get_item_alias(dpg.get_item_parent(series_tag)):
                            dpg.delete_item(series_tag)
                            dpg.add_line_series(
                                [],
                                [],
                                label=f"T7p_CH{channel}",
                                parent=correct_axis,
                                tag=series_tag,
                                show=True,
                            )
                    else:
                        dpg.add_line_series(
                            [],
                            [],
                            label=f"T7p_CH{channel}",
                            parent=correct_axis,
                            tag=series_tag,
                            show=True,
                        )

                    raw_data = T7_Pro_poller.get_data(max(dpg.get_value("main_tab_seconds_lookback"), 1), channel)

                    # here for smooth
                    smooth_y = []
                    if smoothed_boolean:
                        smooth_y = utils.smooth_list(raw_data[1], smooth_length)
                    else:
                        smooth_y = raw_data[1]

                    data = (raw_data[0], smooth_y)

                    dpg.set_value(series_tag, data)
                    dpg.configure_item(series_tag, label=acctive_channel_locations[i])

                    # Setting the data displays on the PNID
                    if len(data[1]) > 0:
                        found = False
                        for tag in pnid_data_tags:
                            # removing the PNID_ prefix on the data label tag
                            trimmed = tag[5:]

                            # if the location prefix matches the data location, and has not been used, data tags have _x suffix
                            if trimmed.startswith(acctive_channel_locations[i].lower()) and not tag in used_pnid_data_tags:
                                used_pnid_data_tags.append(tag)
                                dpg.set_value(tag, str(sigfig_round(data[1][0], 3)) + channel_unit)
                                found = True
                                break

                        if not found:
                            for tag in pnid_data_tags:
                                trimmed = tag[5:]
                                # if the location is custom, we'll just find the first custom location tag to put in it in
                                # and label the respective location with text
                                if trimmed.startswith("custom") and not tag in used_pnid_data_tags:
                                    used_pnid_data_tags.append(tag)
                                    dpg.set_value(
                                        tag,
                                        acctive_channel_locations[i] + ": " + str(sigfig_round(data[1][0], 3)) + channel_unit,
                                    )
                                    found = True
                                    break

                for tag in pnid_data_tags:
                    if tag in used_pnid_data_tags:
                        dpg.show_item(tag)
                    else:
                        dpg.hide_item(tag)

                # Deleting any disabled channels from the plots
                for i in range(24):
                    if not ((i + 1) in active_channels) and dpg.does_item_exist(f"T7p_CH{i+1}_main_plot"):
                        dpg.delete_item(f"T7p_CH{i+1}_main_plot")

                # U6 Pro Updater
                active_channels = U6_Pro_poller.get_active_channels()
                acctive_channel_locations = U6_Pro_poller.get_sensor_locations()

                # pnid_data_tags = main_tab.get_pnid_data_tags()
                # used_pnid_data_tags = []
                for i in range(len(active_channels)):
                    channel = active_channels[i]

                    channel_unit = U6_Pro_poller.get_unit(channel)
                    correct_axis = f"y_axis_{str.lower(channel_unit)}"
                    series_tag = f"U6p_CH{channel}_main_plot"

                    # Seeing if item is already plotted
                    if dpg.does_item_exist(series_tag):
                        # If exists, let's check it's parent axis
                        if correct_axis != dpg.get_item_alias(dpg.get_item_parent(series_tag)):
                            dpg.delete_item(series_tag)
                            dpg.add_line_series(
                                [],
                                [],
                                label=f"U6p_CH{channel}",
                                parent=correct_axis,
                                tag=series_tag,
                                show=True,
                            )
                    else:
                        dpg.add_line_series(
                            [],
                            [],
                            label=f"U6p_CH{channel}",
                            parent=correct_axis,
                            tag=series_tag,
                            show=True,
                        )

                    raw_data = U6_Pro_poller.get_data(max(dpg.get_value("main_tab_seconds_lookback"), 1), channel)

                    # here for smooth
                    smooth_y = []
                    if smoothed_boolean:
                        smooth_y = utils.smooth_list(raw_data[1], smooth_length)
                    else:
                        smooth_y = raw_data[1]

                    data = (raw_data[0], smooth_y)

                    dpg.set_value(series_tag, data)
                    dpg.configure_item(series_tag, label=acctive_channel_locations[i])

                    # Setting the data displays on the PNID
                    if len(data[1]) > 0:
                        found = False
                        for tag in pnid_data_tags:
                            # removing the PNID_ prefix on the data label tag
                            trimmed = tag[5:]

                            # if the location prefix matches the data location, and has not been used, data tags have _x suffix
                            if trimmed.startswith(acctive_channel_locations[i].lower()) and not tag in used_pnid_data_tags:
                                used_pnid_data_tags.append(tag)
                                dpg.set_value(tag, str(sigfig_round(data[1][0], 3)) + channel_unit)
                                found = True
                                break

                        if not found:
                            for tag in pnid_data_tags:
                                trimmed = tag[5:]
                                # if the location is custom, we'll just find the first custom location tag to put in it in
                                # and label the respective location with text
                                if trimmed.startswith("custom") and not tag in used_pnid_data_tags:
                                    used_pnid_data_tags.append(tag)
                                    dpg.set_value(
                                        tag,
                                        acctive_channel_locations[i] + ": " + str(sigfig_round(data[1][0], 3)) + channel_unit,
                                    )
                                    found = True
                                    break

                for tag in pnid_data_tags:
                    if tag in used_pnid_data_tags:
                        dpg.show_item(tag)
                    else:
                        dpg.hide_item(tag)

                # Deleting any disabled channels from the plots
                for i in range(24):
                    if not ((i + 1) in active_channels) and dpg.does_item_exist(f"U6p_CH{i+1}_main_plot"):
                        dpg.delete_item(f"U6p_CH{i+1}_main_plot")

                ecu_pt_active_channels = ECU_Poller.get_ecu_pt_active_channels()
                ecu_pt_locations = ECU_Poller.get_ecu_pt_locations()
                lookback_s = max(dpg.get_value("main_tab_seconds_lookback"), 1)

                for i in range(len(ecu_pt_active_channels)):
                    channel = ecu_pt_active_channels[i]
                    series_tag = f"ECU_PT{channel}_main_plot"

                    if not dpg.does_item_exist(series_tag):
                        dpg.add_line_series(
                            [],
                            [],
                            label=ecu_pt_locations[i],
                            parent="y_axis_psi",
                            tag=series_tag,
                            show=True,
                        )

                    ecu_pt_data = ECU_Poller.get_ecu_pt_data(lookback_s, pt_index=channel - 1)
                    dpg.set_value(series_tag, ecu_pt_data)
                    dpg.configure_item(series_tag, label=ecu_pt_locations[i])

                for channel in range(1, 5):
                    series_tag = f"ECU_PT{channel}_main_plot"
                    if channel not in ecu_pt_active_channels and dpg.does_item_exist(series_tag):
                        dpg.delete_item(series_tag)

                ecu_tc_active_channels = ECU_Poller.get_ecu_tc_active_channels()
                ecu_tc_locations = ECU_Poller.get_ecu_tc_locations()

                for i in range(len(ecu_tc_active_channels)):
                    channel = ecu_tc_active_channels[i]
                    series_tag = f"ECU_TC{channel}_hot_main_plot"

                    if not dpg.does_item_exist(series_tag):
                        dpg.add_line_series(
                            [],
                            [],
                            label=ecu_tc_locations[i],
                            parent="y_axis_c",
                            tag=series_tag,
                            show=True,
                        )

                    ecu_tc_data = ECU_Poller.get_ecu_tc_data(lookback_s, tc_index=channel - 1, junction="hot")
                    dpg.set_value(series_tag, ecu_tc_data)
                    dpg.configure_item(series_tag, label=ecu_tc_locations[i])

                for channel in range(1, 5):
                    series_tag = f"ECU_TC{channel}_hot_main_plot"
                    if channel not in ecu_tc_active_channels and dpg.does_item_exist(series_tag):
                        dpg.delete_item(series_tag)

            # Updating the ECU data every 0.05 seconds
            if cur_time - last_main_ecu_update > 0.05:
                last_main_ecu_update = cur_time

                desired_valve_states = ECU_Poller.get_desired_valve_states()
                actual_valve_states = ECU_Poller.get_actual_valve_states()
                valve_locations = ECU_Poller.get_valve_locations()
                pyro_states = ECU_Poller.get_pyro_channel_states()

                rs485_percentages = ECU_Poller.get_rs485_valve_percentages()  # gets values from ECU_Poller

                valve_tags = main_tab.get_pnid_valve_tags()

                for i in range(0, 36):
                    dpg.set_value(f"valve_loc_{i}", valve_locations[i])

                    percent_tag = f"rs485_valve_{i}"
                    if dpg.does_item_exist(percent_tag):
                        if 12 <= i <= 35 and (i - 12) < len(rs485_percentages):
                            dpg.set_value(percent_tag, f"{rs485_percentages[i - 12]}%")
                        else:
                            dpg.set_value(percent_tag, "-")

                    # Getting the tags of the on PNID states
                    valve_tag = f"PNID_{valve_locations[i].lower()}_valve"
                    on_pnid = valve_tag in valve_tags  # dpg.does_item_exist(f"{valve_tag}_actual")

                    def set_red(tag):
                        dpg.configure_item(tag, color=(255, 0, 0, 150))
                        dpg.configure_item(tag, fill=(255, 0, 0, 150))

                    def set_green(tag):
                        dpg.configure_item(tag, color=(0, 255, 0, 150))
                        dpg.configure_item(tag, fill=(0, 255, 0, 150))

                    if desired_valve_states[i] == 0:
                        dpg.show_item(f"valve_open_button_{i}")
                        dpg.hide_item(f"valve_close_button_{i}")
                        set_red(f"valve_desired_icon_{i}")

                        if on_pnid:
                            set_red(valve_tag + "_desired")

                    else:
                        dpg.show_item(f"valve_close_button_{i}")
                        dpg.hide_item(f"valve_open_button_{i}")
                        set_green(f"valve_desired_icon_{i}")

                        if on_pnid:
                            set_green(valve_tag + "_desired")

                    if actual_valve_states[i] == 0:
                        set_red(f"valve_actual_icon_{i}")
                        if on_pnid:
                            set_red(valve_tag + "_actual")
                    else:
                        set_green(f"valve_actual_icon_{i}")
                        if on_pnid:
                            set_green(valve_tag + "_actual")

                for i in range(2):
                    if pyro_states[i] == 0:
                        set_red(f"pyro_status_icon_{i}")
                    else:
                        set_green(f"pyro_status_icon_{i}")

                # ECU COmmand updates
                sent_command_list = ECU_Poller.get_last_sent_commands(7)

                sent_command_string = ""
                if len(sent_command_list) > 0:
                    for sent in sent_command_list:
                        sent_command_string += sent[1] + " => " + sent[0] + "\n"

                dpg.set_value("main_tab_ecu_sent_commands", sent_command_string)

                recieved_command_list = ECU_Poller.get_last_recieved_commands(7)

                recieved_command_string = ""
                if len(recieved_command_list) > 0:
                    for read in recieved_command_list:
                        recieved_command_string += read[1] + " => " + read[0] + "\n"

                dpg.set_value("main_tab_ecu_recieved_commands", recieved_command_string)

                # ECU Run Sequences
                sequence_names = sequence_executer.get_names()
                dpg.configure_item("main_tab_sequence_select", items=sequence_names)

                selected_sequence = dpg.get_value("main_tab_sequence_select")
                start_enabled = False
                if selected_sequence in sequence_names:
                    selected_index = sequence_names.index(selected_sequence)
                    start_enabled = sequence_executer.is_sequence_uploaded(selected_index)

                dpg.configure_item("main_tab_sequence_start_button", enabled=start_enabled)
                dpg.set_value(
                    "main_tab_step_number",
                    f"{sequence_executer.get_sequence_step()}/{sequence_executer.get_sequence_length()}",
                )
                dpg.set_value(
                    "main_tab_step_time_left",
                    f"for {sequence_executer.get_time_till_next_step():0.1f}s",
                )

        if dpg.get_value("sensor_config_tab"):
            if cur_time - last_sensor_config_update > 0.1:
                active_channels = T7_poller.get_active_channels()
                for i in range(len(active_channels)):
                    channel = active_channels[i]
                    channel_unit = T7_poller.get_unit(channel)
                    value = T7_poller.get_last_value(channel)

                    dpg.set_value(f"reading_T7_CH{channel}", f"{value:.2f} {channel_unit}")

                for channel in range(1, 5):
                    dpg.set_value(f"reading_ECU_PT{channel}", "-")
                    dpg.set_value(f"reading_ECU_TC{channel}", "-")

                ecu_pt_active_channels = ECU_Poller.get_ecu_pt_active_channels()
                for channel in ecu_pt_active_channels:
                    ecu_pt_data = ECU_Poller.get_ecu_pt_data(1, pt_index=channel - 1)
                    if len(ecu_pt_data[1]) > 0:
                        dpg.set_value(f"reading_ECU_PT{channel}", f"{ecu_pt_data[1][0]:.2f} psi")

                ecu_tc_active_channels = ECU_Poller.get_ecu_tc_active_channels()
                for channel in ecu_tc_active_channels:
                    ecu_tc_data = ECU_Poller.get_ecu_tc_data(1, tc_index=channel - 1, junction="hot")
                    if len(ecu_tc_data[1]) > 0:
                        dpg.set_value(f"reading_ECU_TC{channel}", f"{ecu_tc_data[1][0]:.2f} C")

        time.sleep(0.01)
