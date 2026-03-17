from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse
from .models import Project, Appliance
from .engine import (
    calculate_demand_load,
    calculate_current,
    calculate_power_triangle,
    select_mcb,
    select_wire_gauge,
    calculate_voltage_drop,
    balance_phases
)
from .pdf_generator import generate_schedule_pdf

def dashboard(request):
    projects = Project.objects.all().order_by('-created_at')
    project_id = request.GET.get('project_id')
    
    if project_id:
        project = get_object_or_404(Project, id=project_id)
    else:
        project = projects.first()
        if not project:
            project = Project.objects.create(name="New Project")
            
    appliances = project.appliances.all()
    
    # Process calculations
    processed_appliances = []
    total_power = 0
    total_apparent_power = 0
    total_reactive_power = 0
    
    for app in appliances:
        circuit_watts = app.power_watts * app.quantity
        current = calculate_current(circuit_watts, app.power_factor)
        s_va, q_var = calculate_power_triangle(circuit_watts, app.power_factor)
        
        mcb, mcb_type = select_mcb(current, app.appliance_type)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'circuit_watts': circuit_watts,
            'current': round(current, 2),
            'apparent_power': round(s_va, 1),
            'mcb': mcb,
            'mcb_type': mcb_type,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += circuit_watts
        total_apparent_power += s_va
        total_reactive_power += q_var
        
    # Calculate System Power Factor
    system_pf = (total_power / total_apparent_power) if total_apparent_power > 0 else 1.0
    
    # Calculate Demand Load
    demand_load = calculate_demand_load(total_power)
        
    # 3-Phase balancing
    phase_data = balance_phases(appliances)
    
    # Metadata updates
    if total_power != project.total_load or project.phase_type != ("3-Phase" if phase_data.get('requires_3_phase') else "1-Phase"):
        project.total_load = total_power
        project.phase_type = '3-Phase' if phase_data.get('requires_3_phase') else '1-Phase'
        project.save()
    
    context = {
        'projects': projects,
        'project': project,
        'appliances': processed_appliances,
        'total_power': total_power,
        'demand_load': demand_load,
        'total_apparent_power': round(total_apparent_power, 1),
        'total_reactive_power': round(total_reactive_power, 1),
        'system_pf': round(system_pf, 3),
        'phase_data': phase_data,
        'has_failures': any(a['is_failure'] for a in processed_appliances)
    }
    return render(request, 'dashboard.html', context)

def add_appliance(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id')
        if project_id:
            project = get_object_or_404(Project, id=project_id)
        else:
            project, _ = Project.objects.get_or_create(name="New Project")
            
        name = request.POST.get('name')
        appliance_type = request.POST.get('appliance_type', 'Standard')
        quantity = request.POST.get('quantity', 1)
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
                
            try:
                qty = int(quantity)
                if qty < 1: qty = 1
            except ValueError:
                qty = 1
                
            Appliance.objects.create(
                project=project,
                name=name,
                appliance_type=appliance_type,
                quantity=qty,
                power_watts=float(power),
                power_factor=pf,
                length_m=float(length)
            )
    return redirect(f"/?project_id={project.id}" if hasattr(request, 'POST') and request.POST.get('project_id') else 'dashboard')

def remove_appliance(request, app_id):
    appliance = get_object_or_404(Appliance, id=app_id)
    project_id = appliance.project.id
    appliance.delete()
    return redirect(f"/?project_id={project_id}")

def export_pdf(request):
    project_id = request.GET.get('project_id')
    if project_id:
        project = get_object_or_404(Project, id=project_id)
    else:
        project = Project.objects.first()
        
    appliances = project.appliances.all()
    
    processed_appliances = []
    total_power = 0
    total_apparent_power = 0
    
    for app in appliances:
        circuit_watts = app.power_watts * app.quantity
        current = calculate_current(circuit_watts, app.power_factor)
        s_va, _ = calculate_power_triangle(circuit_watts, app.power_factor)
        mcb, mcb_type = select_mcb(current, app.appliance_type)
        wire_size, resistance = select_wire_gauge(current)
        v_drop, v_drop_pct, is_failure = calculate_voltage_drop(app.length_m, current, resistance)
        
        processed_appliances.append({
            'appliance': app,
            'circuit_watts': circuit_watts,
            'current': round(current, 2),
            'apparent_power': round(s_va, 1),
            'mcb': mcb,
            'mcb_type': mcb_type,
            'wire_size': wire_size,
            'v_drop': v_drop,
            'v_drop_pct': v_drop_pct,
            'is_failure': is_failure
        })
        total_power += circuit_watts
        total_apparent_power += s_va
        
    system_pf = (total_power / total_apparent_power) if total_apparent_power > 0 else 1.0    
    demand_load = calculate_demand_load(total_power)
    phase_data = balance_phases(appliances)
    
    # We will pass system_pf and demand_load to generate_schedule_pdf parameter later
    pdf_buffer = generate_schedule_pdf(project.name, processed_appliances, total_power, phase_data, system_pf=system_pf, demand_load=demand_load)
    
    response = FileResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="VoltGuard_Schedule.pdf"'
    
    return response
