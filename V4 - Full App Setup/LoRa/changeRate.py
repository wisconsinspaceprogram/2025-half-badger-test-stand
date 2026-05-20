import serial
import serial.tools.list_ports
import time

# =========================
# USER SETTINGS
# =========================

PORT = "COM4"

# Current baud rate of the LoRa HAT.
# Set to None to auto-detect from COMMON_BAUDS.
OLD_BAUD = None

# New UART baud rate you want.
NEW_BAUD = 115200

# Set these to match your LoRa network.
# Both LoRa modules must have the same frequency, air speed, network ID, etc.
FREQ_MHZ = 915       # Use 915 for US modules, 868 for EU, 433 for 433 MHz modules
ADDRESS = 0x0000     # 0x0000 is common/default
NET_ID = 0x00
AIR_SPEED = 2400     # 2400, 4800, 9600, 19200, 38400, 62500
BUFFER_SIZE = 240    # 240, 128, 64, 32
POWER_DBM = 22       # usually 22, 17, 13, or 10
ENABLE_PACKET_RSSI = False
CRYPT = 0x0000

# Used when OLD_BAUD is None.
COMMON_BAUDS = [9600, 115200, 57600, 38400, 19200, 4800, 2400, 1200]
SCAN_ALL_PORTS_ON_FAIL = True

# =========================
# WAVESHARE / SX126X CONFIG MAPS
# =========================

UART_BAUD_MAP = {
    1200:   0x00,
    2400:   0x20,
    4800:   0x40,
    9600:   0x60,
    19200:  0x80,
    38400:  0xA0,
    57600:  0xC0,
    115200: 0xE0,
}

AIR_SPEED_MAP = {
    2400:  0x02,
    4800:  0x03,
    9600:  0x04,
    19200: 0x05,
    38400: 0x06,
    62500: 0x07,
}

BUFFER_SIZE_MAP = {
    240: 0x00,
    128: 0x40,
    64:  0x80,
    32:  0xC0,
}

POWER_MAP = {
    22: 0x00,
    17: 0x01,
    13: 0x02,
    10: 0x03,
}

def freq_to_offset(freq_mhz: int) -> int:
    """
    Waveshare code does:
      if freq > 850: freq_temp = freq - 850
      elif freq > 410: freq_temp = freq - 410
    """
    if freq_mhz > 850:
        return freq_mhz - 850
    elif freq_mhz > 410:
        return freq_mhz - 410
    else:
        raise ValueError("Frequency should probably be 433, 868, 915, etc.")

def build_config_packet():
    if NEW_BAUD not in UART_BAUD_MAP:
        raise ValueError(f"Unsupported NEW_BAUD: {NEW_BAUD}")

    if AIR_SPEED not in AIR_SPEED_MAP:
        raise ValueError(f"Unsupported AIR_SPEED: {AIR_SPEED}")

    if BUFFER_SIZE not in BUFFER_SIZE_MAP:
        raise ValueError(f"Unsupported BUFFER_SIZE: {BUFFER_SIZE}")

    if POWER_DBM not in POWER_MAP:
        raise ValueError(f"Unsupported POWER_DBM: {POWER_DBM}")

    high_addr = (ADDRESS >> 8) & 0xFF
    low_addr = ADDRESS & 0xFF
    net_id = NET_ID & 0xFF

    # REG0 / address 0x03:
    # bits 7:5 = UART baud
    # bits 2:0 = air speed
    reg0 = UART_BAUD_MAP[NEW_BAUD] + AIR_SPEED_MAP[AIR_SPEED]

    # REG1 / address 0x04:
    # buffer size + power + 0x20, matching Waveshare demo behavior
    reg1 = BUFFER_SIZE_MAP[BUFFER_SIZE] + POWER_MAP[POWER_DBM] + 0x20

    # REG2 / address 0x05:
    # frequency offset
    reg2 = freq_to_offset(FREQ_MHZ) & 0xFF

    # REG3 / address 0x06:
    # Waveshare demo uses 0x43 plus optional packet RSSI enable bit
    rssi_bit = 0x80 if ENABLE_PACKET_RSSI else 0x00
    reg3 = 0x43 + rssi_bit

    crypt_h = (CRYPT >> 8) & 0xFF
    crypt_l = CRYPT & 0xFF

    # Full packet:
    # C0 = permanent write
    # 00 = start register
    # 09 = write 9 bytes, addresses 0x00 through 0x08
    packet = bytes([
        0xC0, 0x00, 0x09,
        high_addr,
        low_addr,
        net_id,
        reg0,
        reg1,
        reg2,
        reg3,
        crypt_h,
        crypt_l,
    ])

    return packet


def read_config(ser: serial.Serial, retries: int = 3):
    """Read 9 config bytes starting at register 0x00.

    Expected response is typically:
      C1 00 09 <9 bytes>
    """
    for _ in range(retries):
        ser.reset_input_buffer()
        ser.write(bytes([0xC1, 0x00, 0x09]))
        ser.flush()
        time.sleep(0.2)
        resp = ser.read(64)
        if len(resp) >= 12 and resp[0] in (0xC0, 0xC1) and resp[1] == 0x00 and resp[2] == 0x09:
            return resp
    return b""


def open_serial(port: str, baud: int):
    return serial.Serial(
        port,
        baudrate=baud,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        write_timeout=1,
    )


def get_candidate_ports():
    ports = [PORT]
    if SCAN_ALL_PORTS_ON_FAIL:
        for p in serial.tools.list_ports.comports():
            if p.device not in ports:
                ports.append(p.device)
    return ports


def detect_current_baud():
    print("Attempting to detect current module UART baud...")
    candidate_ports = get_candidate_ports()

    for port in candidate_ports:
        print(f"Probing port: {port}")
        for baud in COMMON_BAUDS:
            try:
                with open_serial(port, baud) as ser:
                    time.sleep(0.3)
                    resp = read_config(ser, retries=2)
                    if resp:
                        print(f"Detected module on {port} at baud {baud}")
                        return port, baud, resp
                    print(f"  {port} @ {baud}: no config response")
            except Exception as e:
                print(f"  {port} @ {baud}: open/probe failed ({e})")

    return None, None, b""


def build_baud_only_packet_from_readback(read_resp: bytes):
    """Build a C0 permanent-write packet that only changes UART baud.

    This keeps air speed, frequency, power, address, net id, and crypt exactly as-is.
    """
    if len(read_resp) < 12:
        raise ValueError("Invalid readback payload length")

    cfg = list(read_resp[3:12])  # 9 config bytes
    reg0 = cfg[3]

    if NEW_BAUD not in UART_BAUD_MAP:
        raise ValueError(f"Unsupported NEW_BAUD: {NEW_BAUD}")

    # Preserve lower 5 bits (air speed + parity bits), replace UART baud bits only.
    reg0 = (reg0 & 0x1F) | UART_BAUD_MAP[NEW_BAUD]
    cfg[3] = reg0

    return bytes([0xC0, 0x00, 0x09] + cfg)

def write_config(packet, port, old_baud):
    print(f"Opening {port} at old baud {old_baud}...")
    with open_serial(port, old_baud) as ser:
        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("Sending config packet:")
        print(packet.hex(" "))

        ser.write(packet)
        ser.flush()

        # The module may switch baud immediately, so response may or may not appear here.
        time.sleep(0.5)
        resp = ser.read(50)
        print("Response at old baud:", resp.hex(" "))

def test_new_baud(port):
    print(f"\nTesting {port} at new baud {NEW_BAUD}...")
    with open_serial(port, NEW_BAUD) as ser:
        time.sleep(1.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        resp = read_config(ser, retries=5)
        print("Read response at new baud:", resp.hex(" "))

        if len(resp) >= 12 and resp[0] in (0xC0, 0xC1):
            print("SUCCESS: Module responded at 115200.")
        else:
            print("No readable response at 115200.")
            print("This may still have worked if the module changed baud but does not respond to read commands.")

if __name__ == "__main__":
    active_port = PORT
    old_baud = OLD_BAUD
    readback = b""

    if old_baud is None:
        active_port, old_baud, readback = detect_current_baud()
        if old_baud is None:
            print("Could not detect current baud.")
            print("Checked ports:", ", ".join(get_candidate_ports()))
            print("Make sure module is in configuration mode (M0=1, M1=1), then retry.")
            raise SystemExit(1)

    # Read current config at the detected/specified old baud if not already read.
    if not readback:
        try:
            with open_serial(active_port, old_baud) as ser:
                time.sleep(0.4)
                readback = read_config(ser, retries=3)
        except Exception as e:
            print(f"Failed reading config at old baud {old_baud}: {e}")
            raise SystemExit(1)

    if not readback:
        print("No config response from module at old baud.")
        print("Most likely causes: wrong COM port, not in config mode, or wiring issue.")
        raise SystemExit(1)

    config_packet = build_baud_only_packet_from_readback(readback)

    print("About to configure LoRa HAT with:")
    print(f"  Port:        {active_port}")
    print(f"  Old baud:    {old_baud}")
    print(f"  New baud:    {NEW_BAUD}")
    print(f"  Frequency:   {FREQ_MHZ} MHz")
    print(f"  Address:     0x{ADDRESS:04X}")
    print(f"  Net ID:      0x{NET_ID:02X}")
    print(f"  Air speed:   {AIR_SPEED}")
    print(f"  Buffer size: {BUFFER_SIZE}")
    print(f"  Power:       {POWER_DBM} dBm")
    print()

    write_config(config_packet, active_port, old_baud)
    test_new_baud(active_port)

    print("\nDone.")
    print("Now put the HAT back into normal mode:")
    print("  M0: grounded / jumper installed")
    print("  M1: grounded / jumper installed")
    print(f"Then open {active_port} at {NEW_BAUD} in your app.")