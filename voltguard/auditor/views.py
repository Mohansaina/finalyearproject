from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from .models import Project, Appliance
from .engine import (
    calculate_current,
    calculate_power_triangle,
    select_mcb,
    select_wire_gauge,
    calculate_voltage_drop,
    balance_phases
)
from .pdf_generator import generate_schedule_pdf

def dashboard(request):
    # For demonstration, we'll just use a single default project
    project, created = Project.objects.get_or_create(name="Default Project")
    appliances = project.appliances.all()
    
    # Process calculations
    processed_appliances = []
    total_power = 0
    total_apparent_power = 0
    total_reactive_power = 0
    
    for app in appliances:
        current = calculate_current(app.power_watts, app.power_factor)
        s_va, q_var = calculate_power_triangle(app.power_watts, app.power_factor)
        
        mcb = select_mcb(current)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'current': round(current, 2),
            'apparent_power': round(s_va, 1),
            'mcb': mcb,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += app.power_watts
        total_apparent_power += s_va
        total_reactive_power += q_var
        
    # Calculate System Power Factor
    system_pf = (total_power / total_apparent_power) if total_apparent_power > 0 else 1.0
        
    # 3-Phase balancing
    phase_data = balance_phases(appliances)
    
    context = {
        'project': project,
        'appliances': processed_appliances,
        'total_power': total_power,
        'total_apparent_power': round(total_apparent_power, 1),
        'total_reactive_power': round(total_reactive_power, 1),
        'system_pf': round(system_pf, 3),
        'phase_data': phase_data,
        'has_failures': any(a['is_failure'] for a in processed_appliances)
    }
    return render(request, 'dashboard.html', context)

def add_appliance(request):
    if request.method == 'POST':
        project, _ = Project.objects.get_or_create(name="Default Project")
        name = request.POST.get('name')
        power = request.POST.get('power_watts')
        power_factor = request.POST.get('power_factor', '1.0')
        length = request.POST.get('length_m')
        
        if name and power and length:
            try:
                pf = float(power_factor)
                if pf <= 0 or pf > 1.0:
                    pf = 1.0
            except ValueError:
                pf = 1.0
                
            Appliance.objects.create(
                project=project,
                name=name,
                power_watts=float(power),
                power_factor=pf,
                length_m=float(length)
            )
    return redirect('dashboard')

def remove_appliance(request, app_id):
    appliance = get_object_or_404(Appliance, id=app_id)
    appliance.delete()
    return redirect('dashboard')

def export_pdf(request):
    project, _ = Project.objects.get_or_create(name="Default Project")
    appliances = project.appliances.all()
    
    processed_appliances = []
    total_power = 0
    total_apparent_power = 0
    
    for app in appliances:
        current = calculate_current(app.power_watts, app.power_factor)
        s_va, _ = calculate_power_triangle(app.power_watts, app.power_factor)
        mcb = select_mcb(current)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'current': round(current, 2),
            'apparent_power': round(s_va, 1),
            'mcb': mcb,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += app.power_watts
        total_apparent_power += s_va
        
    system_pf = (total_power / total_apparent_power) if total_apparent_power > 0 else 1.0    
    phase_data = balance_phases(appliances)
    
    # We will pass system_pf to generate_schedule_pdf parameter later
    pdf_buffer = generate_schedule_pdf(project.name, processed_appliances, total_power, phase_data, system_pf=system_pf)
    
    response = FileResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="VoltGuard_Schedule.pdf"'
    
    return response
