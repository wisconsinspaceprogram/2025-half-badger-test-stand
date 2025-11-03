import dearpygui.dearpygui as dpg
from pathlib import Path
from core import sequence_executer

sequence_list_tags = []
sequence_names = []
sequence_tables = []
sequence_number_tags = []
sequence_operation_tags = []
sequence_valve_tags = []
sequence_custom_valve_locations = []
sequence_pyro_tags = []
sequence_delay_tags = []
sequence_step_delete_tags = []
sequence_move_up_tags = []
sequence_move_down_tags = []

active_sequence = ""

save_sequence_data = ""

sequence_valve_locations = [
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
    "Custom",
]
pyro_options = ["Pyro 0", "Pyro 1"]


def callback_select_sequence(app_data):
    global active_sequence

    new_index = sequence_list_tags.index(app_data)

    if active_sequence != "":
        old_index = sequence_list_tags.index(active_sequence)
        dpg.hide_item(sequence_tables[old_index])

    dpg.show_item(sequence_tables[new_index])

    active_sequence = app_data

    # Updating the name text box
    dpg.set_value("sequence_tab_name_text_input", sequence_names[new_index])


def callback_add_sequence():
    tag = f"sequence_selectable_left_menu_{len(sequence_list_tags)+1}"
    dpg.add_button(label=f"Sequence {len(sequence_list_tags)+1}", parent="sequence_select_group", tag=tag, callback=callback_select_sequence)

    table_tag = f"sequence_tables_{len(sequence_list_tags)+1}"
    with dpg.table(
        header_row=True,
        row_background=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
        height=900,
        tag=table_tag,
        parent="sequence_edit_section",
        show=False,
    ):
        dpg.add_table_column(label="Sequence Step", init_width_or_weight=0.1)
        dpg.add_table_column(label="Step Command", init_width_or_weight=0.9)
        dpg.add_table_column(label="Delete Step", init_width_or_weight=0.05)
        dpg.add_table_column(label="Move Step", init_width_or_weight=0.05)

    sequence_list_tags.append(tag)
    sequence_names.append(f"Sequence {len(sequence_list_tags)}")
    sequence_tables.append(table_tag)
    sequence_number_tags.append([])
    sequence_operation_tags.append([])
    sequence_valve_tags.append([])
    sequence_custom_valve_locations.append([])
    sequence_pyro_tags.append([])
    sequence_delay_tags.append([])
    sequence_step_delete_tags.append([])
    sequence_move_up_tags.append([])
    sequence_move_down_tags.append([])


def callback_update_name():
    if active_sequence != "":
        index = sequence_list_tags.index(active_sequence)
        new_name = dpg.get_value("sequence_tab_name_text_input")
        sequence_names[index] = new_name
        dpg.configure_item(sequence_list_tags[index], label=new_name)


def callback_change_action(Sender, app_data, user_data):
    combo_tag = f"{user_data}_operation_combo"
    valve_tag = f"{user_data}_valve_location"
    custom_valve_tag = f"{user_data}_custom_valve_location"
    pyro_tag = f"{user_data}_pyro_channel"
    delay_tag = f"{user_data}_delay_input"

    combo_value = dpg.get_value(combo_tag)
    if combo_value == "Open" or combo_value == "Close":
        dpg.show_item(valve_tag)
        dpg.show_item(custom_valve_tag)
        dpg.hide_item(pyro_tag)
        dpg.hide_item(delay_tag)
    elif combo_value == "Fire":
        dpg.hide_item(valve_tag)
        dpg.hide_item(custom_valve_tag)
        dpg.show_item(pyro_tag)
        dpg.hide_item(delay_tag)
    elif combo_value == "Poll":
        dpg.hide_item(valve_tag)
        dpg.hide_item(custom_valve_tag)
        dpg.hide_item(pyro_tag)
        dpg.hide_item(delay_tag)
    else:
        dpg.hide_item(valve_tag)
        dpg.hide_item(custom_valve_tag)
        dpg.hide_item(pyro_tag)
        dpg.show_item(delay_tag)


def callback_remove_step(Sender, app_data, user_data):
    sequence_index = user_data[0]
    step_index = user_data[1]
    # Starting at the index to "remove and shifting all the values up one"
    i = step_index
    #  dpg.delete_item(sequence_number_tags[sequence_index][step_index])
    #  dpg.delete_item(sequence_operation_tags[sequence_index][step_index])
    #  dpg.delete_item(sequence_valve_tags[sequence_index][step_index])
    #  dpg.delete_item(sequence_custom_valve_locations[sequence_index][step_index])
    #  dpg.delete_item(sequence_pyro_tags[sequence_index][step_index])
    #  dpg.delete_item(sequence_delay_tags[sequence_index][step_index])
    #  dpg.delete_item(sequence_step_delete_tags[sequence_index][step_index])\
    if len(sequence_number_tags[sequence_index]) > 1:
        while not i > (len(sequence_number_tags[sequence_index]) - 2):
            dpg.set_value(sequence_operation_tags[sequence_index][i], dpg.get_value(sequence_operation_tags[sequence_index][i + 1]))
            dpg.set_value(sequence_valve_tags[sequence_index][i], dpg.get_value(sequence_valve_tags[sequence_index][i + 1]))
            dpg.set_value(sequence_custom_valve_locations[sequence_index][i], dpg.get_value(sequence_custom_valve_locations[sequence_index][i + 1]))
            dpg.set_value(sequence_pyro_tags[sequence_index][i], dpg.get_value(sequence_pyro_tags[sequence_index][i + 1]))
            dpg.set_value(sequence_delay_tags[sequence_index][i], dpg.get_value(sequence_delay_tags[sequence_index][i + 1]))

            dpg.configure_item(sequence_operation_tags[sequence_index][i], show=dpg.is_item_visible(sequence_operation_tags[sequence_index][i + 1]))
            dpg.configure_item(sequence_valve_tags[sequence_index][i], show=dpg.is_item_visible(sequence_valve_tags[sequence_index][i + 1]))
            dpg.configure_item(
                sequence_custom_valve_locations[sequence_index][i], show=dpg.is_item_visible(sequence_custom_valve_locations[sequence_index][i + 1])
            )
            dpg.configure_item(sequence_pyro_tags[sequence_index][i], show=dpg.is_item_visible(sequence_pyro_tags[sequence_index][i + 1]))
            dpg.configure_item(sequence_delay_tags[sequence_index][i], show=dpg.is_item_visible(sequence_delay_tags[sequence_index][i + 1]))

            i += 1
    parent_row = dpg.get_item_parent(sequence_number_tags[sequence_index][-1])
    dpg.delete_item(sequence_number_tags[sequence_index][-1])
    dpg.delete_item(sequence_operation_tags[sequence_index][-1])
    dpg.delete_item(sequence_valve_tags[sequence_index][-1])
    dpg.delete_item(sequence_custom_valve_locations[sequence_index][-1])
    dpg.delete_item(sequence_pyro_tags[sequence_index][-1])
    dpg.delete_item(sequence_delay_tags[sequence_index][-1])
    dpg.delete_item(sequence_step_delete_tags[sequence_index][-1])
    dpg.delete_item(sequence_move_up_tags[sequence_index][-1])
    dpg.delete_item(sequence_move_down_tags[sequence_index][-1])
    dpg.delete_item(parent_row)

    sequence_number_tags[sequence_index].pop()
    sequence_operation_tags[sequence_index].pop()
    sequence_valve_tags[sequence_index].pop()
    sequence_custom_valve_locations[sequence_index].pop()
    sequence_pyro_tags[sequence_index].pop()
    sequence_delay_tags[sequence_index].pop()
    sequence_step_delete_tags[sequence_index].pop()
    sequence_move_up_tags[sequence_index].pop()
    sequence_move_down_tags[sequence_index].pop()


def swap_step_data(sequence_index, step_a, step_b):
    tags_a = [
        sequence_operation_tags[sequence_index][step_a],
        sequence_valve_tags[sequence_index][step_a],
        sequence_custom_valve_locations[sequence_index][step_a],
        sequence_pyro_tags[sequence_index][step_a],
        sequence_delay_tags[sequence_index][step_a],
    ]
    tags_b = [
        sequence_operation_tags[sequence_index][step_b],
        sequence_valve_tags[sequence_index][step_b],
        sequence_custom_valve_locations[sequence_index][step_b],
        sequence_pyro_tags[sequence_index][step_b],
        sequence_delay_tags[sequence_index][step_b],
    ]

    # Swap widget values and visibility
    for tag_a, tag_b in zip(tags_a, tags_b):
        val_a = dpg.get_value(tag_a)
        val_b = dpg.get_value(tag_b)
        dpg.set_value(tag_a, val_b)
        dpg.set_value(tag_b, val_a)

        vis_a = dpg.is_item_visible(tag_a)
        vis_b = dpg.is_item_visible(tag_b)
        dpg.configure_item(tag_a, show=vis_b)
        dpg.configure_item(tag_b, show=vis_a)


def callback_move_step_up(sender, app_data, user_data=None):
    """Moves a step one position up in its sequence (ignored if at top)."""
    for seq_idx, move_tags in enumerate(sequence_move_up_tags):
        if sender in move_tags:
            step_idx = move_tags.index(sender)
            # Don't move if already the first step
            if step_idx == 0:
                return
            swap_step_data(seq_idx, step_idx, step_idx - 1)
            return


def callback_move_step_down(sender, app_data, user_data=None):
    """Moves a step one position down in its sequence (ignored if at bottom)."""
    for seq_idx, move_tags in enumerate(sequence_move_down_tags):
        if sender in move_tags:
            step_idx = move_tags.index(sender)
            # Don't move if already the last step
            if step_idx >= len(sequence_move_down_tags[seq_idx]) - 1:
                return
            swap_step_data(seq_idx, step_idx, step_idx + 1)
            return


def add_blank_sequence_row():
    if active_sequence != "":
        index = sequence_list_tags.index(active_sequence)
        step_tag = active_sequence + "_step_" + str(len(sequence_number_tags[index]) + 1)
        sequence_number_tags[index].append(step_tag)
        with dpg.table_row(parent=sequence_tables[index]):
            dpg.add_text(str(len(sequence_number_tags[index])), tag=step_tag)
            with dpg.group(horizontal=True):
                combo_tag = f"{step_tag}_operation_combo"
                valve_tag = f"{step_tag}_valve_location"
                custom_valve_tag = f"{step_tag}_custom_valve_location"
                pyro_tag = f"{step_tag}_pyro_channel"
                delay_tag = f"{step_tag}_delay_input"

                dpg.add_combo(
                    ["Open", "Close", "Fire", "Wait", "Poll"],
                    width=150,
                    tag=combo_tag,
                    callback=callback_change_action,
                    user_data=step_tag,
                    show=True,
                )
                dpg.add_combo(sequence_valve_locations, width=150, tag=valve_tag, show=False)
                dpg.add_input_text(default_value="", hint="Custom Location", width=150, tag=custom_valve_tag, show=False)
                dpg.add_combo(pyro_options, width=150, tag=pyro_tag, show=False)
                dpg.add_input_double(label="Seconds", width=100, min_value=0, tag=delay_tag, show=False)

                sequence_operation_tags[index].append(combo_tag)
                sequence_valve_tags[index].append(valve_tag)
                sequence_custom_valve_locations[index].append(custom_valve_tag)
                sequence_pyro_tags[index].append(pyro_tag)
                sequence_delay_tags[index].append(delay_tag)

            delete_tag = f"{step_tag}_delete_tag"
            dpg.add_button(label="X", callback=callback_remove_step, user_data=(index, len(sequence_number_tags[index]) - 1), tag=delete_tag)
            sequence_step_delete_tags[index].append(delete_tag)

            with dpg.group(horizontal=True):
                dpg.add_button(label="^", tag=f"{step_tag}_up_tag", callback=callback_move_step_up)
                dpg.add_button(label="v", tag=f"{step_tag}_down_tag", callback=callback_move_step_down)

                sequence_move_up_tags[index].append(f"{step_tag}_up_tag")
                sequence_move_down_tags[index].append(f"{step_tag}_down_tag")


def callback_delete_sequence_button():
    if active_sequence != "":
        viewport_width = dpg.get_viewport_client_width()
        viewport_height = dpg.get_viewport_client_height()

        # Calculate center position
        pos_x = (viewport_width - 200) // 2
        pos_y = (viewport_height - 100) // 2

        dpg.configure_item("sequence_delete_popup", pos=(pos_x, pos_y), width=200, height=100)

        dpg.show_item("sequence_delete_popup")


def callback_confirm_delete():
    global active_sequence

    dpg.hide_item("sequence_delete_popup")
    old_index = sequence_list_tags.index(active_sequence)
    dpg.delete_item(sequence_tables[old_index])
    dpg.delete_item(sequence_list_tags[old_index])
    dpg.set_value("sequence_tab_name_text_input", "")
    active_sequence = ""

    sequence_list_tags.pop(old_index)
    sequence_names.pop(old_index)
    sequence_tables.pop(old_index)
    sequence_number_tags.pop(old_index)
    sequence_operation_tags.pop(old_index)
    sequence_valve_tags.pop(old_index)
    sequence_custom_valve_locations.pop(old_index)
    sequence_pyro_tags.pop(old_index)
    sequence_delay_tags.pop(old_index)
    sequence_step_delete_tags.pop(old_index)
    sequence_move_up_tags.pop(old_index)
    sequence_move_down_tags.pop(old_index)


def callback_cancel_delete():
    dpg.hide_item("sequence_delete_popup")


def generate_sequence_text(sequence_index):
    out_string = sequence_names[sequence_index]

    for step in range(len(sequence_number_tags[sequence_index])):
        out_string += f"\n{dpg.get_value(sequence_operation_tags[sequence_index][step])},{dpg.get_value(sequence_valve_tags[sequence_index][step])},{dpg.get_value(sequence_custom_valve_locations[sequence_index][step])},{dpg.get_value(sequence_pyro_tags[sequence_index][step])},{dpg.get_value(sequence_delay_tags[sequence_index][step])}"

    return out_string + "\n"


def generate_sequence_list(sequence_index):
    out_list = []

    for step in range(len(sequence_number_tags[sequence_index])):
        out_list.append(
            [
                dpg.get_value(sequence_operation_tags[sequence_index][step]),
                dpg.get_value(sequence_valve_tags[sequence_index][step]),
                dpg.get_value(sequence_custom_valve_locations[sequence_index][step]),
                dpg.get_value(sequence_pyro_tags[sequence_index][step]),
                dpg.get_value(sequence_delay_tags[sequence_index][step]),
            ]
        )

    return out_list


def callback_save_sequences():
    global save_sequence_data

    save_sequence_data = ""
    for i in range(len(sequence_list_tags)):
        save_sequence_data += "###\n"
        save_sequence_data += generate_sequence_text(i)

    dpg.show_item("sequence_save_dialog")


def callback_save_sequence_confirm(sender, app_data, user_data):
    path = app_data["file_path_name"]
    try:
        with open(path, "w") as file:
            file.write(save_sequence_data)
        # print(f"Saved to {path}")
    except Exception as e:
        print(f"Failed to save file: {e}")


def callback_open_sequences():
    dpg.show_item("sequence_open_dialog")


def callback_open_sequence_confirm(sender, app_data, user_data):
    try:
        path = app_data["file_path_name"]
        raw_csv_lines = []
        csv_lines = []
        with open(path, "r") as file:
            raw_csv_lines = file.readlines()
        for line in raw_csv_lines:
            csv_lines.append(line.strip())

        next_line_name = False
        for line in csv_lines:
            if line == "###":
                callback_add_sequence()
                callback_select_sequence(sequence_list_tags[-1])
                next_line_name = True

            elif next_line_name:
                next_line_name = False
                dpg.set_value("sequence_tab_name_text_input", line)
                callback_update_name()
                # "Updated_name")

            else:
                add_blank_sequence_row()

                info = line.split(",")

                dpg.set_value(sequence_operation_tags[sequence_list_tags.index(active_sequence)][-1], info[0])
                dpg.set_value(sequence_valve_tags[sequence_list_tags.index(active_sequence)][-1], info[1])
                dpg.set_value(sequence_custom_valve_locations[sequence_list_tags.index(active_sequence)][-1], info[2])
                dpg.set_value(sequence_pyro_tags[sequence_list_tags.index(active_sequence)][-1], info[3])
                dpg.set_value(sequence_delay_tags[sequence_list_tags.index(active_sequence)][-1], float(info[4]))

                callback_change_action(
                    None, None, active_sequence + "_step_" + str(len(sequence_number_tags[sequence_list_tags.index(active_sequence)]))
                )
    except Exception as e:
        print(e)


def callback_apply_sequences():
    sequence_datas = []
    for sequence in range(len(sequence_list_tags)):
        sequence_datas.append(generate_sequence_list(sequence))

    sequence_executer.update_sequence_steps(sequence_datas)
    sequence_executer.update_sequence_names(sequence_names)


def load_defaults():
    this_file_dir = Path(__file__).parent
    file_path = this_file_dir.parent / "save_files" / "defaults" / "default_sequences.csv"
    callback_open_sequence_confirm(None, {"file_path_name": file_path}, None)
    callback_apply_sequences()


def build():
    with dpg.tab(label="Sequences", tag="sequence_tab"):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Apply", user_data=None, callback=callback_apply_sequences)
            dpg.add_button(label="Add Sequence From File", callback=callback_open_sequences)
            dpg.add_button(label="Save Sequences To File", callback=callback_save_sequences)

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_save_sequence_confirm,
            id="sequence_save_dialog",
            modal=True,
            width=500,
            height=400,
            label="Save sequences",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.file_dialog(
            directory_selector=False,
            show=False,
            callback=callback_open_sequence_confirm,
            id="sequence_open_dialog",
            modal=True,
            width=500,
            height=400,
            label="Open sequences",
        ):
            dpg.add_file_extension(".csv", color=(255, 255, 255, 255))

        with dpg.table(
            header_row=True, row_background=False, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True, height=900
        ):

            dpg.add_table_column(label="Select Sequence", init_width_or_weight=0.075)
            dpg.add_table_column(label="Sequence Editor", init_width_or_weight=0.9)

            with dpg.table_row():
                with dpg.group(tag="sequence_select_group"):

                    dpg.add_button(label="+ Add Sequence", callback=callback_add_sequence)

                    # with dpg.table(header_row=False, row_background=True,
                    #               borders_innerH=True, borders_outerH=True, borders_innerV=True,
                    #               borders_outerV=True, height=900):

                with dpg.window(label="Confirm Delete Sequence?", modal=True, show=False, tag="sequence_delete_popup"):
                    dpg.add_text(f"Are you sure?")
                    dpg.add_separator()
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Yes, delete", callback=callback_confirm_delete)
                        dpg.add_button(label="Cancel", callback=callback_cancel_delete)

                with dpg.group(tag="sequence_edit_section"):
                    with dpg.group(horizontal=True):
                        dpg.add_text("Sequence Name: ")
                        dpg.add_input_text(default_value="", hint="Name", width=300, tag="sequence_tab_name_text_input")
                        dpg.add_button(label="Update", callback=callback_update_name)
                        dpg.add_button(label="Delete Sequence", callback=callback_delete_sequence_button)

                    dpg.add_button(label="Add New Step: +", callback=add_blank_sequence_row)
