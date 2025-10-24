import dearpygui.dearpygui as dpg
from . import main_tab, valve_config_tab, sensor_config_tab, sequence_tab

def build_tabs():
  with dpg.tab_bar(tag='tag_bar'):
    main_tab.build()
    valve_config_tab.build()
    sensor_config_tab.build()
    sequence_tab.build()

def load_defaults():
    valve_config_tab.load_defaults()
    sensor_config_tab.load_defaults()
    sequence_tab.load_defaults()  
    