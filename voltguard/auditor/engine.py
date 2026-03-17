"""
VoltGuard Engineering Engine
Core calculating module for all electrical formulas, including Power Factor.
"""
import math

def calculate_demand_load(total_power, diversity_factor=0.8):
    """
    Calculate practical Demand Load by applying a diversity factor.
    """
    return total_power * diversity_factor

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

def select_mcb(current, appliance_type='Standard'):
    """
    Select MCB rating and Type (B or C).
    Motor/AC appliances use a 125% Safety Factor and 'Type C'.
    Lights use 'Type B'.
    """
    if appliance_type == 'Motor/AC':
        safety_current = float(current) * 1.25
        mcb_type = 'C'
    elif appliance_type == 'Light':
        safety_current = float(current) * 1.0
        mcb_type = 'B'
    else:
        # Standard load
        safety_current = float(current) * 1.25
        mcb_type = 'B'
        
    standard_ratings = [6, 10, 16, 20, 25, 32, 40, 63]
    
    for rating in standard_ratings:
        if rating >= safety_current:
            return rating, mcb_type
    
    # Exceeds standard ratings, returning max
    return 63, mcb_type

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
    3-Phase Balancer: If total load > 7kW, distribute appliances across L1, L2, L3 phases
    to minimize neutral current.
    Uses a greedy descending algorithm based on power.
    
    appliances: list of Appliance model instances or dictionaries with 'name' and 'power_watts'.
    Returns: dictionary with L1, L2, L3 lists of appliances and 'requires_3_phase' boolean.
    """
    # Handle total power taking into account quantity if present via a helper
    def get_power(app):
        if hasattr(app, 'quantity'):
            return app.power_watts * app.quantity
        return app.power_watts

    total_power = sum(get_power(app) for app in appliances)
    
    if total_power <= 7000:
        return {
            'requires_3_phase': False,
            'L1': appliances,
            'L2': [],
            'L3': [],
            'Loads': {'L1': total_power, 'L2': 0, 'L3': 0}
        }
        
    # Sort appliances by power descending
    sorted_apps = sorted(appliances, key=lambda x: get_power(x), reverse=True)
    phases = {'L1': [], 'L2': [], 'L3': []}
    phase_loads = {'L1': 0, 'L2': 0, 'L3': 0}
    
    for app in sorted_apps:
        # Find phase with minimum load
        min_phase = min(phase_loads, key=phase_loads.get)
        phases[min_phase].append(app)
        phase_loads[min_phase] += get_power(app)
        
    return {
        'requires_3_phase': True,
        'L1': phases['L1'],
        'L2': phases['L2'],
        'L3': phases['L3'],
        'Loads': phase_loads
    }
