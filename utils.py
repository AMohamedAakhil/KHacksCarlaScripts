import random


def calculate_pressure(initial_pressure: float, uptime: int, stopped_for: int):
    # pressure is in psi
    # uptime is in seconds
    # tire pressure increases by 1 psi for every 5 minutes, for 20 minutes. then it stays constant
    # tire pressure decreases by 1 psi for every 5 minutes of stopping, for 20 minutes. then it stays constant
    if uptime <= 1200:
        return initial_pressure + uptime / 300 - stopped_for / 300
    else:
        if stopped_for >= 1200:
            return initial_pressure
        return initial_pressure + 4 - stopped_for / 300


def is_seatbelt(uptime: int, stopped_for: int):
    # uptime is in seconds
    # seatbelt is on after stopping for random time between 10 and 30 seconds
    # seatbelt is off after stopping for random time between 0 and 10 seconds
    if stopped_for < 10:
        return False
    if uptime > 30:
        return True

    if uptime > random.randint(10, 30) or stopped_for > random.randint(0, 10):
        return True

    return False


def get_vehicle_inclination(rotation):
    # The pitch component of the rotation is the inclination
    pitch = rotation.pitch
    return pitch

def calculate_engine_rpm(current_gear: int, gear_ratio: float, final_drive_ratio: float,
                         current_speed: float, rolling_radius: float):
    # current speed in m/s
    # rolling radius in meters
    rpm = (current_speed*60) / (2 * 3.14 * rolling_radius)
    if current_gear > 0:
        rpm = rpm * gear_ratio * final_drive_ratio
    return rpm


#
# def calculate_engine_rpm(gear_ratio: float, max_rpm: float, throttle: float, final_ratio: float):
#     return (max_rpm * throttle) / (final_ratio * gear_ratio)
