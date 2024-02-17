import math

# Define constants for engine wear
MAX_ENGINE_OIL_PERCENTAGE = 100
MIN_ENGINE_OIL_PERCENTAGE = 0
MAX_TIME_BEFORE_OIL_CHANGE = 365 * 24 * 60 * 60  # 1 year in seconds

def estimate_engine_oil_percentage(vehicle_info, time_passed_seconds):
    # Calculate engine wear based on time passed
    time_percentage = min(1, time_passed_seconds / MAX_TIME_BEFORE_OIL_CHANGE)
    
    # Calculate engine wear based on vehicle factors
    vehicle_wear_factors = [
        vehicle_info["Vehicle Speed"],
        vehicle_info["Vehicle Acceleration"],
        vehicle_info["Vehicle Throttle"],
        vehicle_info["Vehicle Brake"],
        vehicle_info["Vehicle Steer"],
        vehicle_info["Vehicle Gear"],
        vehicle_info["Vehicle Manual Gear Shift"],
        vehicle_info["Vehicle Hand Brake"],
        vehicle_info["tire friction of tire 1"],
        vehicle_info["max_rpm"],
        vehicle_info["accelerometer"],
    ]
    
    # Example: Calculate a combined wear factor based on vehicle factors
    combined_vehicle_wear_factor = sum(vehicle_wear_factors) / (len(vehicle_wear_factors) * 100)
    
    # Calculate estimated engine oil percentage based on time and vehicle wear
    estimated_percentage = MAX_ENGINE_OIL_PERCENTAGE - (MAX_ENGINE_OIL_PERCENTAGE - MIN_ENGINE_OIL_PERCENTAGE) * (time_percentage + combined_vehicle_wear_factor)
    
    # Ensure the result is within bounds
    estimated_percentage = max(MIN_ENGINE_OIL_PERCENTAGE, min(MAX_ENGINE_OIL_PERCENTAGE, estimated_percentage))
    
    return estimated_percentage

# Example usage:
vehicle_info = {
    "Vehicle Speed": 50,
    "Vehicle Acceleration": 2,
    "Vehicle Throttle": 0.7,
    "Vehicle Brake": 0.2,
    "Vehicle Steer": 0.1,
    "Vehicle Gear": 3,
    "Vehicle Manual Gear Shift": False,
    "Vehicle Hand Brake": False,
    "tire friction of tire 1": 0.8,
    "max_rpm": 6000,
    "accelerometer": 2,
}

# Assuming 6 months (approx. 15778463 seconds) have passed
time_passed_seconds = 1

estimated_oil_percentage = estimate_engine_oil_percentage(vehicle_info, time_passed_seconds)
print("Estimated Engine Oil Percentage:", estimated_oil_percentage)
