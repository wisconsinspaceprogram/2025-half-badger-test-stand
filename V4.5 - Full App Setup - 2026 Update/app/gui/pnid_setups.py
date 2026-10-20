import dearpygui.dearpygui as dpg
from pathlib import Path

# The P&ID is laid out in "image pixels" on a 700x700 image. Every overlay item is
# recorded here so rescale_pnid() can resize the image and move the overlays with it.
PNID_BASE_SIZE = 700
PNID_IMAGE_TAG = "pnid_image"
DATA_LINE_SPACING = 10

# (item tag, anchor x, anchor y, fixed dx, fixed dy)
# pos = origin + anchor * scale + fixed offset   (text / icons themselves don't scale)
_layout_items = []


def _reset_layout():
    _layout_items.clear()


def _add_pnid_image(texture_tag, origin):
    dpg.add_image(texture_tag, tag=PNID_IMAGE_TAG, pos=origin, width=PNID_BASE_SIZE, height=PNID_BASE_SIZE)


def make_data_stack(location: str, start: tuple, offset: tuple, count: int, up: bool):
    pnid_data_tags = []

    for i in range(count):
        tag = f"PNID_{location.lower()}_data_{i}"
        dy = DATA_LINE_SPACING * (-i if up else i)
        dpg.add_text(
            default_value="22.1c",
            tag=tag,
            pos=(offset[0] + start[0], offset[1] + start[1] + dy),
            show=True,
        )
        _layout_items.append((tag, start[0], start[1], 0, dy))
        pnid_data_tags.append(tag)

    return pnid_data_tags


def make_pnid_valve_icons(location: str, start: tuple, offset: tuple):
    pnid_valve_tags = []

    tag = f"PNID_{location.lower()}_valve"
    pnid_valve_tags.append(tag)
    with dpg.group(pos=(offset[0] + start[0], offset[1] + start[1]), tag=tag + "_group"):
        with dpg.drawlist(25, 25):
            dpg.draw_rectangle((0, 0), (25, 25), color=(0, 255, 0, 255), fill=(0, 255, 0, 200), tag=tag + "_desired")
            dpg.draw_circle((12.5, 12.5), radius=7, color=(255, 0, 0, 255), fill=(255, 0, 0, 200), tag=tag + "_actual")

    # Anchor on the icon's centre so it stays over the valve symbol when the image shrinks/grows
    _layout_items.append((tag + "_group", start[0] + 12.5, start[1] + 12.5, -12.5, -12.5))
    return pnid_valve_tags


def rescale_pnid(scale: float, origin: tuple = (0, 0)):
    """Resize the P&ID image and reposition every overlay to match."""
    if dpg.does_item_exist(PNID_IMAGE_TAG):
        size = int(PNID_BASE_SIZE * scale)
        dpg.configure_item(PNID_IMAGE_TAG, width=size, height=size, pos=(int(origin[0]), int(origin[1])))

    for tag, ax, ay, dx, dy in _layout_items:
        if dpg.does_item_exist(tag):
            dpg.configure_item(tag, pos=(int(origin[0] + ax * scale + dx), int(origin[1] + ay * scale + dy)))


def build_full_setup():
    pnid_data_tags = []
    pnid_valve_tags = []

    width, height, channels, data = dpg.load_image(str(Path(__file__).parents[1] / "assets" / "images" / "BasicP&ID.png"))

    with dpg.texture_registry(show=False):
        dpg.add_static_texture(width=width, height=height, default_value=data, tag="P&ID Image")

    # Positions are relative to the container the P&ID is built in (the P&ID panel on the main tab)
    pnid_location = (0, 0)
    _reset_layout()
    _add_pnid_image("P&ID Image", pnid_location)
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

    # Positions are relative to the container the P&ID is built in (the P&ID panel on the main tab)
    pnid_location = (0, 0)
    _reset_layout()
    _add_pnid_image("P&ID Image", pnid_location)
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


def build_fall_2026_setup():
    pnid_data_tags = []
    pnid_valve_tags = []

    width, height, channels, data = dpg.load_image(str(Path(__file__).parents[1] / "assets" / "images" / "pnid_2026.png"))

    with dpg.texture_registry(show=False):
        dpg.add_static_texture(width=width, height=height, default_value=data, tag="P&ID Image")

    pnid_location = (0, 0)
    _reset_layout()
    _add_pnid_image("P&ID Image", pnid_location)
    pnid_data_tags.extend(make_data_stack("GN2 Bottle", (360, 72), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Tank Top", (210, 127), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Tank Bottom", (210, 303), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Venturi Inlet", (126, 356), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Venturi Throat", (126, 397), pnid_location, count=2, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Venturi Outlet", (126, 436), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("LOX Manifold", (215, 555), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Tank Top", (434, 127), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Tank Bottom", (512, 303), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Venturi Inlet", (518, 356), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Venturi Throat", (518, 397), pnid_location, count=2, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Venturi Outlet", (518, 436), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("IPA Manifold", (436, 555), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("Purge Bottle", (360, 293), pnid_location, count=3, up=False))
    pnid_data_tags.extend(make_data_stack("Combustion Chamber", (410, 599), pnid_location, count=2, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 1", (240, 598), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 2", (240, 614), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 3", (240, 630), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 4", (240, 646), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 5", (240, 662), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("TCA 6", (240, 678), pnid_location, count=1, up=False))
    pnid_data_tags.extend(make_data_stack("Custom", (12, 545), pnid_location, count=15, up=False))

    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Press", (262.5, 17.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Press", (412.5, 17.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Tank Vent", (97.5, 82.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Tank Vent", (577.5, 82.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill", (127.5, 295.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Fill Vent", (47.5, 277.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Main", (217.5, 477.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Main", (457.5, 477.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("LOX Purge", (227.5, 367.5), pnid_location))
    pnid_valve_tags.extend(make_pnid_valve_icons("IPA Purge", (447.5, 367.5), pnid_location))

    valve_locs = [
        "LOX Press",
        "IPA Press",
        "LOX Tank Vent",
        "IPA Tank Vent",
        "LOX Fill",
        "LOX Fill Vent",
        "LOX Main",
        "IPA Main",
        "LOX Purge",
        "IPA Purge",
        "Not Connected",
    ]
    sensor_locs = [
        "GN2 Bottle",
        "LOX Tank Top",
        "LOX Tank Bottom",
        "LOX Venturi Inlet",
        "LOX Venturi Throat",
        "LOX Venturi Outlet",
        "LOX Manifold",
        "IPA Tank Top",
        "IPA Tank Bottom",
        "IPA Venturi Inlet",
        "IPA Venturi Throat",
        "IPA Venturi Outlet",
        "IPA Manifold",
        "Purge Bottle",
        "Combustion Chamber",
        "TCA 1",
        "TCA 2",
        "TCA 3",
        "TCA 4",
        "TCA 5",
        "TCA 6",
        "Custom",
        "Not Connected",
    ]

    return pnid_data_tags, pnid_valve_tags, valve_locs, sensor_locs