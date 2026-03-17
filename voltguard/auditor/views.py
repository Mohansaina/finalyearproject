from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from .models import Project, Appliance
from .engine import (
    calculate_current,
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
    
    for app in appliances:
        current = calculate_current(app.power_watts)
        mcb = select_mcb(current)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'current': round(current, 2),
            'mcb': mcb,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += app.power_watts
        
    # 3-Phase balancing
    phase_data = balance_phases(appliances)
    
    context = {
        'project': project,
        'appliances': processed_appliances,
        'total_power': total_power,
        'phase_data': phase_data,
        'has_failures': any(a['is_failure'] for a in processed_appliances)
    }
    return render(request, 'dashboard.html', context)

def add_appliance(request):
    if request.method == 'POST':
        project, _ = Project.objects.get_or_create(name="Default Project")
        name = request.POST.get('name')
        power = request.POST.get('power_watts')
        length = request.POST.get('length_m')
        
        if name and power and length:
            Appliance.objects.create(
                project=project,
                name=name,
                power_watts=float(power),
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
    
    for app in appliances:
        current = calculate_current(app.power_watts)
        mcb = select_mcb(current)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'current': round(current, 2),
            'mcb': mcb,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += app.power_watts
        
    phase_data = balance_phases(appliances)
    
    pdf_buffer = generate_schedule_pdf(project.name, processed_appliances, total_power, phase_data)
    
    response = FileResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="VoltGuard_Schedule.pdf"'
    
    return response
