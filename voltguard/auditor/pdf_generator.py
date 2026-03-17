import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_schedule_pdf(project_name, appliances, total_power, phase_data, system_pf=1.0, demand_load=0.0, main_mcb_rating=63, main_mcb_type='C'):
    """
    Generates a PDF using reportlab with all calculations, warnings, and Phase Distribution
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=40, bottomMargin=40)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=18, spaceAfter=20)
    elements.append(Paragraph(f"Electrical Wiring Schedule: {project_name}", title_style))
    
    # System Overview
    elements.append(Paragraph(f"<b>Total Connected Real Load:</b> {round(total_power, 1)} W", styles['Normal']))
    elements.append(Paragraph(f"<b>Demand Load (0.8 Diversity Factor):</b> {round(demand_load, 1)} W", styles['Normal']))
    elements.append(Paragraph(f"<b>Main Incomer Rating:</b> {main_mcb_rating}A (Type {main_mcb_type})", styles['Normal']))
    
    # System PF Status
    pf_color = "green" if system_pf >= 0.9 else ("#b45309" if system_pf >= 0.8 else "red")
    elements.append(Paragraph(f"<b>System Power Factor (Overall):</b> <font color='{pf_color}'>{round(system_pf, 3)}</font>", styles['Normal']))
    
    if system_pf < 0.85:
        elements.append(Paragraph("<i><font color='red'>Warning: Poor Power Factor. Capacitor Bank Recommended.</font></i>", styles['Normal']))

    supply_type = "3-Phase (Exceeds 7kW limit)" if phase_data.get('requires_3_phase') else "1-Phase (Standard)"
    elements.append(Paragraph(f"<b>System Supply Type:</b> {supply_type}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Appliances Table
    data = [['Appliance', 'Qty', 'S (VA)', 'P.F.', 'Current (A)', 'MCB', 'Wire', 'V.Drop', 'Status']]
    
    has_failure = False
    
    for item in appliances:
        status_text = "FAILURE (>3%)" if item['is_failure'] else "OK"
        wire_display = f"{item['wire_size']}mm²"
        
        if item['is_failure']:
            has_failure = True
            wire_display = f"Upgrade: {item['suggested_gauge']}mm²"
            
        data.append([
            item['appliance'].name[:12],
            f"{item['appliance'].quantity}",
            f"{item['apparent_power']}",
            f"{item['appliance'].power_factor}",
            f"{item['current']}",
            f"{item['mcb']}A ({item['mcb_type']})",
            wire_display,
            f"{item['v_drop']}V ({item['v_drop_pct']}%)",
            status_text
        ])
        
    # Create Table
    table = Table(data, colWidths=[90, 30, 50, 30, 60, 50, 60, 80, 70])
    
    table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ])
    
    # Highlight failures
    for i, row in enumerate(data[1:], 1):
        if row[8] == "FAILURE (>3%)":
            table_style.add('TEXTCOLOR', (8, i), (8, i), colors.red)
            table_style.add('FONTNAME', (8, i), (8, i), 'Helvetica-Bold')
            
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Warning Note if any failure
    if has_failure:
        warning_style = ParagraphStyle('Warning', parent=styles['Normal'], textColor=colors.red)
        elements.append(Paragraph("<b>WARNING:</b> One or more circuits exceed the 3% voltage drop limit. A larger wire gauge is required.", warning_style))
        elements.append(Spacer(1, 15))
    
    # Phase Balancing Details
    if phase_data.get('requires_3_phase'):
        elements.append(Paragraph("<b>3-Phase Load Distribution:</b>", styles['Heading3']))
        loads = phase_data.get('Loads', {'L1': 0, 'L2': 0, 'L3': 0})
        phase_text = f"Phase L1: {round(loads.get('L1', 0), 1)}W | " \
                     f"Phase L2: {round(loads.get('L2', 0), 1)}W | " \
                     f"Phase L3: {round(loads.get('L3', 0), 1)}W"
        elements.append(Paragraph(phase_text, styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<i>Note: Appliances have been distributed to minimize neutral current.</i>", styles['Italic']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
