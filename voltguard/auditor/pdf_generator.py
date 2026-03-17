import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_schedule_pdf(project_name, appliances, total_power, phase_data):
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
    elements.append(Paragraph(f"<b>Total Connected Load:</b> {round(total_power, 1)} W", styles['Normal']))
    supply_type = "3-Phase (Exceeds 7kW limit)" if phase_data.get('requires_3_phase') else "1-Phase (Standard)"
    elements.append(Paragraph(f"<b>System Supply Type:</b> {supply_type}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # Appliances Table
    data = [['Appliance', 'Power (W)', 'Current (A)', 'MCB (A)', 'Wire (mm²)', 'V. Drop (V)', 'Status']]
    
    has_failure = False
    
    for item in appliances:
        status_text = "FAILURE (>3%)" if item['is_failure'] else "OK"
        if item['is_failure']:
            has_failure = True
            
        data.append([
            item['appliance'].name,
            f"{item['appliance'].power_watts}",
            f"{item['current']}",
            f"{item['mcb']}",
            f"{item['wire_size']}",
            f"{item['v_drop']} ({item['v_drop_pct']}%)",
            status_text
        ])
        
    # Create Table
    table = Table(data, colWidths=[120, 60, 60, 50, 60, 90, 80])
    
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
        if row[6] == "FAILURE (>3%)":
            table_style.add('TEXTCOLOR', (6, i), (6, i), colors.red)
            table_style.add('FONTNAME', (6, i), (6, i), 'Helvetica-Bold')
            
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
        loads = phase_data.get('Loads', {'R': 0, 'Y': 0, 'B': 0})
        phase_text = f"Red (R) Phase: {round(loads.get('R', 0), 1)}W | " \
                     f"Yellow (Y) Phase: {round(loads.get('Y', 0), 1)}W | " \
                     f"Blue (B) Phase: {round(loads.get('B', 0), 1)}W"
        elements.append(Paragraph(phase_text, styles['Normal']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<i>Note: Appliances have been distributed to minimize neutral current.</i>", styles['Italic']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
