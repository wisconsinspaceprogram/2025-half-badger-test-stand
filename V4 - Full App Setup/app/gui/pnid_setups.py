import dearpygui.dearpygui as dpg
from pathlib import Path

# fix this all


def make_data_stack(location: str, start: tuple, offset: tuple, count: int, up: bool):
    pnid_data_tags = []

    for i in range(count):
        tag = f"PNID_{location.lower()}_data_{i}"
        dpg.add_text(
            default_value="22.1c",
            tag=tag,
            pos=((offset[0] + start[0], offset[1] + start[1] + 10 * (-i if up else i))),
            show=True,
        )
        pnid_data_tags.append(tag)

    return pnid_data_tags


def make_pnid_valve_icons(location: str, start: tuple, offset: tuple):
    pnid_valve_tags = []

    tag = f"PNID_{location.lower()}_valve"
    pnid_valve_tags.append(tag)
    with dpg.group(pos=(offset[0] + start[0], offset[1] + start[1])):
        with dpg.drawlist(25, 25):
            dpg.draw_rectangle((0, 0), (25, 25), color=(0, 255, 0, 255), fill=(0, 255, 0, 200), tag=tag + "_desired")
            dpg.draw_circle((12.5, 12.5), radius=7, color=(255, 0, 0, 255), fill=(255, 0, 0, 200), tag=tag + "_actual")

    return pnid_valve_tags


def build_full_setup():
    pnid_data_tags = []
    pnid_valve_tags = []

    width, height, channels, data = dpg.load_image(str(Path(__file__).parents[1] / "assets" / "images" / "BasicP&ID.png"))

    with dpg.texture_registry(show=False):
        dpg.add_static_texture(width=width, height=height, default_value=data, tag="P&ID Image")

    pnid_location = (400, 0)
    dpg.add_image("P&ID Image", pos=pnid_location, width=700, height=700)
    pnid_data_tags.extend(make_data_stack("LOX Tank Top", (210, 110), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("LOX Tank Bottom", (265, 202), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("LOX Venturi", (545, 245), pnid_location, count=5, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Manifold", (560, 380), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("IPA Manifold", (560, 485), pnid_location, count=5, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Tank Bottom", (210, 615), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("IPA Tank Top", (150, 510), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("Combustion Chamber", (660, 425), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("Custom", (50, 150), pnid_location, count=15, up=False))

    pnid_valve_tags.extend(make_pnid_valve_icons("GN2 Main", (179, 394), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Tank Vent", (59, 499), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Fill Dump", (59, 594), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Purge", (367, 474), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Purge", (367, 341), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Main", (499, 538), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Main", (499, 329), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Venturi Vent", (500, 144), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Venturi Iso", (392, 184), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill", (305, 144), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill Vent", (388, 53), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Tank Vent", (130, 90), pnid_location))

    valve_locs = [
        "GN2 Main",
        "IPA Tank Vent",
        "IPA Fill Dump",
        "IPA Purge",
        "LOX Purge",
        "IPA Main",
        "LOX Main",
        "LOX Venturi Vent",
        "LOX Venturi Iso",
        "LOX Fill",
        "LOX Fill Vent",
        "LOX Tank Vent",
    ]
    sensor_locs = [ 
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

    return pnid_data_tags, pnid_valve_tags, valve_locs, sensor_locs


def build_nov_9_hotfire_setup():
    pnid_data_tags = []
    pnid_valve_tags = []

    width, height, channels, data = dpg.load_image(str(Path(__file__).parents[1] / "assets" / "images" / "hotfire_config_nov_9.png"))

    with dpg.texture_registry(show=False):
        dpg.add_static_texture(width=width, height=height, default_value=data, tag="P&ID Image")

    pnid_location = (400, 0)
    dpg.add_image("P&ID Image", pos=pnid_location, width=700, height=700)
    pnid_data_tags.extend(make_data_stack("LOX Tank Top", (210, 110), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("LOX Tank Bottom", (265, 202), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("LOX Venturi", (545, 245), pnid_location, count=5, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Manifold", (560, 380), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("IPA Manifold", (560, 485), pnid_location, count=5, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Tank Bottom", (210, 615), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("IPA Tank Top", (150, 510), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("Combustion Chamber", (660, 425), pnid_location, count=5, up=True))
    pnid_data_tags.extend(make_data_stack("Custom", (50, 150), pnid_location, count=15, up=False))

    pnid_valve_tags.extend(make_pnid_valve_icons("GN2 Main", (179, 394), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Tank Vent", (59, 499), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Fill Dump", (59, 594), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Purge", (367, 474), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Purge", (367, 341), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Main", (499, 538), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Main", (499, 329), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill", (305, 144), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill Vent", (388, 53), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Tank Vent", (130, 90), pnid_location))

    valve_locs = [
        "GN2 Main",
        "IPA Tank Vent",
        "IPA Fill Dump",
        "IPA Purge",
        "LOX Purge",
        "IPA Main",
        "LOX Main",
        "LOX Fill",
        "LOX Fill Vent",
        "LOX Tank Vent",
        "Not Connected"
    ]
    sensor_locs = [
        "LOX Tank Top",
        "LOX Tank Bottom",
        "LOX Venturi",
        "LOX Manifold",
        "IPA Manifold",
        "IPA Tank Bottom",
        "IPA Tank Top",
        "Combustion Chamber",
        "Custom",
        "Not Connected"
    ]

    return pnid_data_tags, pnid_valve_tags, valve_locs, sensor_locs
