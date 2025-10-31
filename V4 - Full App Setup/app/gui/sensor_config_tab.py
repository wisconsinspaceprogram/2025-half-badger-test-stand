import dearpygui.dearpygui as dpg
from gui import T7_daq_config, T7_pro_daq_config


def build():
    with dpg.tab(label="Sensor Config", tag="sensor_config_tab"):
        T7_daq_config.build()
        T7_pro_daq_config.build()


def load_defaults():
    T7_daq_config.load_defaults()
    T7_pro_daq_config.load_defaults()
