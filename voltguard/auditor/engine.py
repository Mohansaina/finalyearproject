"""
VoltGuard Engineering Engine
Core calculating module for all electrical formulas, including Power Factor.
"""
import math

def calculate_demand_load(total_power_watts, diversity_factor=0.8):
    """
    Calculate practical Demand Load by applying a diversity factor.
    """
    return float(total_power_watts) * diversity_factor

def calculate_power_triangle(power_watts, power_factor):
    """
    Calculate Apparent Power (VA) and Reactive Power (VAr).
    S = P / PF
    Q = sqrt(S^2 - P^2)
    Returns: (apparent_power_va, reactive_power_var)
    """
    if power_factor <= 0:
        return 0.0, 0.0
        
    p = float(power_watts)
    pf = float(power_factor)
    
    # Apparent Power (S) in VA
    apparent_power_va = p / pf
    
    # Reactive Power (Q) in VAr
    # Q = S * sin(acos(pf)) or sqrt(S^2 - P^2)
    reactive_power_var = math.sqrt(max(0, apparent_power_va**2 - p**2))
    
    return apparent_power_va, reactive_power_var

def calculate_current(apparent_power_va, voltage=230.0, is_3_phase=False):
    """
    Calculate Total Current.
    Formula: 
    1-Phase: I = S / V
    3-Phase: I = S / (V * sqrt(3))
    """
    if voltage <= 0 or apparent_power_va <= 0:
        return 0.0
    
    if is_3_phase:
        return float(apparent_power_va) / (float(voltage) * math.sqrt(3))
    
    return float(apparent_power_va) / float(voltage)

def select_mcb(current, appliance_type='Standard'):
    """
    Select MCB rating and Type (B or C).
    - 125% Safety Factor Rule: I_mcb >= 1.25 * I_load for ALL circuits
    - Motor/AC use 'Type C'. Loads typically use 'Type B' or 'C'.
    """
    safety_current = float(current) * 1.25
    
    if appliance_type == 'Motor/AC':
        mcb_type = 'C'
    elif appliance_type == 'Light':
        mcb_type = 'B'
    else:
        mcb_type = 'B'
        
    standard_ratings = [6, 10, 16, 20, 25, 32, 40, 63, 80, 100, 125, 160]
    
    for rating in standard_ratings:
        if rating >= safety_current:
            return rating, mcb_type
    
    # Exceeds standard ratings, returning max
    return 160, mcb_type

def suggest_main_incomer(demand_load_watts, voltage=230, is_3_phase=False):
    """
    Suggests the Main Incomer rating based on the total Demand Load.
    """
    apparent_power_va, _ = calculate_power_triangle(demand_load_watts, 1.0) # Assume 1.0 PF for incomer rough calc if not factored
    current = calculate_current(apparent_power_va, voltage, is_3_phase)
    rating, mcb_type = select_mcb(current, 'Standard')
    return rating, mcb_type

def select_wire_gauge(current):
    """
    Select Standard Copper Wire Gauge based on Ampacity and exact Copper Resistances.
    Lookup Table:
    1.5 mm2 -> up to 16A -> 12.1 ohm/km
    2.5 mm2 -> up to 25A -> 7.41 ohm/km
    4.0 mm2 -> up to 32A -> 4.61 ohm/km
    6.0 mm2 -> up to 40A -> 3.08 ohm/km
    10.0 mm2 -> up to 63A -> 1.83 ohm/km
    
    Returns a tuple: (gauge_mm2, resistance_per_km)
    """
    if current <= 16:
        return (1.5, 12.1)
    elif current <= 25:
        return (2.5, 7.41)
    elif current <= 32:
        return (4.0, 4.61)
    elif current <= 40:
        return (6.0, 3.08)
    else:
        return (10.0, 1.83)

def calculate_voltage_drop(length_m, current, gauge_mm2, resistance_per_km, voltage=230.0):
    """
    Auditor for Voltage Drop.
    Formula: V_drop = (2 * L * I * R) / 1000
    L = length in meters, I = current in Amps, R = Resistance per km (Ohms/km)
    
    Returns: (v_drop, percentage_drop, is_failure, warning_msg, suggested_gauge_mm2)
    """
    v_drop = (2 * length_m * current * resistance_per_km) / 1000.0
    voltage_drop_percent = (v_drop / voltage) * 100
    
    # Auto-Upgrade Logic for V_drop > 3%
    is_failure = voltage_drop_percent > 3.0
    warning_msg = None
    suggested_gauge_mm2 = gauge_mm2
    
    if is_failure:
        # Array of tuples: (gauge_mm2, resistance_per_km)
        larger_sizes = [(2.5, 7.41), (4.0, 4.61), (6.0, 3.08), (10.0, 1.83), (16.0, 1.15)]
        
        for next_gauge, next_res in larger_sizes:
            if next_gauge > gauge_mm2:
                test_v_drop = (2 * length_m * current * next_res) / 1000.0
                test_percentage = (test_v_drop / voltage) * 100
                if test_percentage <= 3.0:
                    suggested_gauge_mm2 = next_gauge
                    warning_msg = f"Safety Warning: V_drop > 3%. Suggest auto-upgrading to {next_gauge}mm² wire."
                    break
        
        if not warning_msg:
            warning_msg = f"Critical Danger: V_drop {round(voltage_drop_percent, 1)}% exceeds 3% limits and wire is too thick for branch circuit."

    return round(v_drop, 2), round(voltage_drop_percent, 2), is_failure, warning_msg, suggested_gauge_mm2

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

def calculate_energy_and_carbon(total_watts, hours_per_day, days_per_month=30):
    """
    Predict monthly energy footprint and cost.
    Assumes standard price of ₹8.0 per Unit (kWh) and 0.85 kg CO2 per Unit.
    """
    monthly_kwh = (total_watts * hours_per_day * days_per_month) / 1000.0
    monthly_cost_inr = monthly_kwh * 8.0
    monthly_carbon_kg = monthly_kwh * 0.85
    return monthly_kwh, monthly_cost_inr, monthly_carbon_kg

def estimate_bom_cost(processed_appliances, main_mcb_rating):
    """
    Provides a real-world Bill of Materials (BoM) estimate in INR.
    Parses the already calculated arrays to estimate hardware costs.
    """
    total_cost = 0.0
    
    # 1. Main Incomer Cost
    if main_mcb_rating <= 63:
        total_cost += 1500  # Standard Main switch/ELCB
    else:
        total_cost += 3500  # Heavy Duty MCCB

    # 2. Wire & Branch MCBs
    for item in processed_appliances:
        # MCB Pricing
        if item['mcb_type'] == 'C':
            total_cost += 350  # Type C inductive breakers
        else:
            total_cost += 250  # Type B resistive breakers
            
        # Copper Wire Pricing per meter based on physical limits
        gauge = item.get('suggested_gauge', item['wire_size'])
        length = item['appliance'].length_m
        
        if gauge <= 1.5:
            rate = 20
        elif gauge <= 2.5:
            rate = 35
        elif gauge <= 4.0:
            rate = 55
        elif gauge <= 6.0:
            rate = 85
        else:
            rate = 150
            
        total_cost += (length * rate)
        
    return total_cost
