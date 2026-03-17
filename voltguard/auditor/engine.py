"""
VoltGuard Engineering Engine
Core calculating module for all electrical formulas, including Power Factor.
"""
import math

def calculate_current(power_watts, power_factor=1.0, voltage=230.0):
    """
    Calculate Total Current.
    Formula: I = P / (V * PF)
    """
    if voltage <= 0 or power_factor <= 0:
        return 0.0
    return float(power_watts) / (float(voltage) * float(power_factor))

def calculate_power_triangle(power_watts, power_factor):
    """
    Calculate Apparent Power (VA) and Reactive Power (VAr).
    S = P / PF
    Q = sqrt(S^2 - P^2)
    """
    if power_factor <= 0:
        return 0.0, 0.0
        
    p = float(power_watts)
    pf = float(power_factor)
    
    # Apparent Power (S) in VA
    s = p / pf
    
    # Reactive Power (Q) in VAr
    # Q = S * sin(acos(pf)) or sqrt(S^2 - P^2)
    q = math.sqrt(max(0, s**2 - p**2))
    
    return s, q

def select_mcb(current):
    """
    Select MCB rating implementing the 125% Safety Rule for continuous loads.
    Formula: Minimum MCB = I * 1.25
    Standard Ratings: 6A, 10A, 16A, 20A, 25A, 32A, 40A, 63A
    """
    safety_current = float(current) * 1.25
    standard_ratings = [6, 10, 16, 20, 25, 32, 40, 63]
    
    for rating in standard_ratings:
        if rating >= safety_current:
            return rating
    
    # Exceeds standard ratings, returning max
    return 63

def select_wire_gauge(current):
    """
    Select Standard Copper Wire Gauge based on Ampacity.
    Lookup Table:
    1.0 mm2 -> up to 12A
    1.5 mm2 -> up to 16A
    2.5 mm2 -> up to 25A
    4.0 mm2 -> up to 32A
    6.0 mm2 -> up to 40A
    
    Returns a tuple: (mm2, resistance_per_km_in_ohms)
    """
    if current <= 12:
        return (1.0, 18.1)
    elif current <= 16:
        return (1.5, 12.1)
    elif current <= 25:
        return (2.5, 7.41)
    elif current <= 32:
        return (4.0, 4.61)
    else:
        return (6.0, 3.08)

def calculate_voltage_drop(length_m, current, resistance_per_km, voltage=230.0):
    """
    Auditor for Voltage Drop.
    Formula: V_drop = (2 * L * I * R) / 1000
    L = length in meters, I = current in Amps, R = Resistance per km (Ohms/km)
    
    Returns: (v_drop, percentage_drop, is_failure)
    """
    v_drop = (2 * length_m * current * resistance_per_km) / 1000.0
    percentage = (v_drop / voltage) * 100
    is_failure = percentage > 3.0
    
    return round(v_drop, 2), round(percentage, 2), is_failure

def balance_phases(appliances):
    """
    3-Phase Balancer: If total load > 7kW, distribute appliances across R, Y, B phases
    to minimize neutral current.
    Uses a greedy descending algorithm based on power.
    
    appliances: list of Appliance model instances or dictionaries with 'name' and 'power_watts'.
    Returns: dictionary with R, Y, B lists of appliances and 'requires_3_phase' boolean.
    """
    total_power = sum(app.power_watts for app in appliances)
    
    if total_power <= 7000:
        return {
            'requires_3_phase': False,
            'R': appliances,
            'Y': [],
            'B': [],
            'Loads': {'R': total_power, 'Y': 0, 'B': 0}
        }
        
    # Sort appliances by power descending
    sorted_apps = sorted(appliances, key=lambda x: x.power_watts, reverse=True)
    phases = {'R': [], 'Y': [], 'B': []}
    phase_loads = {'R': 0, 'Y': 0, 'B': 0}
    
    for app in sorted_apps:
        # Find phase with minimum load
        min_phase = min(phase_loads, key=phase_loads.get)
        phases[min_phase].append(app)
        phase_loads[min_phase] += app.power_watts
        
    return {
        'requires_3_phase': True,
        'R': phases['R'],
        'Y': phases['Y'],
        'B': phases['B'],
        'Loads': phase_loads
    }
