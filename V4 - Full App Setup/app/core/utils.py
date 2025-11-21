def mv_to_c_type_k(mv: float) -> float:
    """
    Convert millivolts (mV) to degrees Celsius (°C) for a Type K thermocouple using
    NIST ITS-90 reference polynomial with a cold junction at 0 °C.

    Parameters:
        mv (float): Thermocouple voltage in millivolts.

    Returns:
        float: Estimated hot junction temperature in degrees Celsius.
    """

    # NIST Type K inverse coefficients for different mV ranges
    # Each set is for mv range: (-5.891, 0.000), (0.000, 20.644), and (20.644, 54.886)
    if mv < 0.000:
        # if -5.891 <= mv < 0.000:
        c = [0.0000000e00, 2.5173462e01, -1.1662878e00, -1.0833638e00, -8.9773540e-01, -3.7342377e-01, -8.6632643e-02, -1.0450598e-02, -5.1920577e-04]
    elif 0.000 <= mv < 20.644:
        c = [
            0.000000e00,
            2.508355e01,
            7.860106e-02,
            -2.503131e-01,
            8.315270e-02,
            -1.228034e-02,
            9.804036e-04,
            -4.413030e-05,
            1.057734e-06,
            -1.052755e-08,
        ]
    elif 20.644 <= mv <= 54.886:
        c = [-1.318058e02, 4.830222e01, -1.646031e00, 5.464731e-02, -9.650715e-04, 8.802193e-06, -3.110810e-08]
    else:
        raise ValueError("Input voltage out of range for Type K thermocouple (-5.891 to 54.886 mV)")

    # Compute temperature in °C using the polynomial
    t = 0.0
    for i, coef in enumerate(c):
        t += coef * (mv**i)
    return t


def c_to_mv_type_k(temp_c: float) -> float:
    """
    Convert °C to mV for a Type K thermocouple using NIST reference (cold junction compensation).
    Valid for -270 to 1372 °C.
    """
    if -270 <= temp_c < 0:
        c = [
            0.000000000000e00,
            3.9450128025e-02,
            2.3622373598e-05,
            -3.2858906784e-07,
            -4.9904828777e-09,
            -6.7509059173e-11,
            -5.7410327428e-13,
            -3.1088872894e-15,
            -1.0451609365e-17,
            -1.9889266878e-20,
            -1.6322697486e-23,
        ]
    elif 0 <= temp_c <= 1372:
        c = [
            -0.176004136860e-01,
            0.389212049750e-01,
            0.185587700320e-04,
            -0.994575928740e-07,
            0.318409457190e-09,
            -0.560728448890e-12,
            0.560750590590e-15,
            -0.320207200030e-18,
            0.971511471520e-22,
            -0.121047212750e-25,
        ]
    else:
        raise ValueError("Temperature out of range for Type K thermocouple (-270 to 1372 °C)")

    mv = 0.0
    for i, coef in enumerate(c):
        mv += coef * (temp_c**i)
    return mv


def mv_to_c_type_t(mv: float) -> float:
    """
    Convert millivolts (mV) to degrees Celsius for a Type T thermocouple.
    Based on NIST ITS-90 inverse polynomial.
    Range: -5.603 mV to +20.872 mV (≈ -270 °C to +400 °C)
    """
    if mv < 0.0:
        c = [0.0000000e00, 2.5949192e01, -2.1316967e-01, 7.9018692e-01, 4.2527777e-01, 1.3304473e-01, 2.0241446e-02, 1.2668171e-03]
    elif 0.0 <= mv <= 20.872:
        c = [0.000000e00, 2.592800e01, -7.602961e-01, 4.637791e-02, -2.165394e-03, 6.048144e-05, -7.293422e-07]
    else:
        raise ValueError("Input mV out of range for Type T thermocouple (-5.603 to 20.872 mV)")

    t = 0.0
    for i, coef in enumerate(c):
        t += coef * (mv**i)
    return t


def c_to_mv_type_t(temp_c: float) -> float:
    """
    Convert degrees Celsius to millivolts (mV) for a Type T thermocouple.
    Based on NIST ITS-90 forward polynomial.
    Range: -270 °C to +400 °C
    """
    if -270.0 <= temp_c < 0.0:
        c = [
            0.000000000000e00,
            3.874810636400e-02,
            5.283398650000e-05,
            -7.390255719000e-06,
            3.326111119000e-07,
            9.999946000000e-09,
            -1.528860000000e-10,
            1.245840000000e-12,
            -4.034300000000e-15,
        ]
    elif 0.0 <= temp_c <= 400.0:
        c = [
            0.000000000000e00,
            3.874810636400e-02,
            3.329222788000e-05,
            2.061824340000e-07,
            -2.188225684000e-09,
            1.099688092000e-11,
            -3.081575877000e-14,
            4.547913529000e-17,
            -2.751290167000e-20,
        ]
    else:
        raise ValueError("Temperature out of range for Type T thermocouple (-270 to 400 °C)")

    mv = 0.0
    for i, coef in enumerate(c):
        mv += coef * (temp_c**i)
    return mv

# Moving Average Calculator 
# data should be a 1D list
# length should be a smoothing period
def smooth_list(data: list,length: int):
    new_data = []
    if length >= len(data):
        pass
    else:
        for i in range(len(data)):
            largest_number = max(0, i - length + 1)
            window = data[largest_number:i+1]
            new_data.append(sum(window) / len(window))
    return new_data

