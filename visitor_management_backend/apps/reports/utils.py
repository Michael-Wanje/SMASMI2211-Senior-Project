import io
import xlsxwriter
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_excel_report(entries, report_date):
    """Generate Excel report for daily visitor entries"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Daily Visitor Report')
    
    # Define formats
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center'
    })
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BC',
        'border': 1
    })
    cell_format = workbook.add_format({
        'border': 1,
        'align': 'left'
    })
    
    # Title
    worksheet.merge_range('A1:H1', f'Daily Visitor Report - {report_date}', title_format)
    worksheet.write('A2', f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
    
    # Headers
    headers = [
        'Entry Time', 'Visitor Name', 'Phone', 'National ID', 
        'Resident', 'Purpose', 'Status', 'Recorded By'
    ]
    
    for col, header in enumerate(headers):
        worksheet.write(3, col, header, header_format)
    
    # Data
    for row, entry in enumerate(entries, start=4):
        worksheet.write(row, 0, entry.entry_time.strftime('%H:%M:%S'), cell_format)
        worksheet.write(row, 1, entry.visitor.full_name, cell_format)
        worksheet.write(row, 2, entry.visitor.phone_number, cell_format)
        worksheet.write(row, 3, entry.visitor.national_id, cell_format)
        
        resident_name = 'Walk-in'
        if entry.visit_request and entry.visit_request.resident:
            resident_name = f"{entry.visit_request.resident.first_name} {entry.visit_request.resident.last_name}"
        worksheet.write(row, 4, resident_name, cell_format)
        
        purpose = entry.visit_request.purpose if entry.visit_request else 'Walk-in Visit'
        worksheet.write(row, 5, purpose, cell_format)
        worksheet.write(row, 6, entry.status.title(), cell_format)
        
        recorded_by = f"{entry.recorded_by.first_name} {entry.recorded_by.last_name}" if entry.recorded_by else 'System'
        worksheet.write(row, 7, recorded_by, cell_format)
    
    # Summary
    summary_row = len(entries) + 6
    worksheet.write(summary_row, 0, 'SUMMARY:', header_format)
    worksheet.write(summary_row + 1, 0, f'Total Entries: {len(entries)}')
    worksheet.write(summary_row + 2, 0, f'Approved Entries: {len([e for e in entries if e.status == "approved"])}')
    worksheet.write(summary_row + 3, 0, f'Pending Entries: {len([e for e in entries if e.status == "pending"])}')
    
    # Adjust column widths
    worksheet.set_column('A:A', 12)
    worksheet.set_column('B:B', 20)
    worksheet.set_column('C:C', 15)
    worksheet.set_column('D:D', 15)
    worksheet.set_column('E:E', 20)
    worksheet.set_column('F:F', 25)
    worksheet.set_column('G:G', 12)
    worksheet.set_column('H:H', 20)
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="daily_visitor_report_{report_date}.xlsx"'
    
    return response

def generate_pdf_report(entries, report_date):
    """Generate PDF report for daily visitor entries"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    # Title
    title = Paragraph(f'Daily Visitor Report - {report_date}', title_style)
    elements.append(title)
    
    # Generation info
    gen_info = Paragraph(
        f'Generated on: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}',
        styles['Normal']
    )
    elements.append(gen_info)
    elements.append(Spacer(1, 20))
    
    # Summary
    summary_data = [
        ['Summary', ''],
        ['Total Entries', str(len(entries))],
        ['Approved Entries', str(len([e for e in entries if e.status == 'approved']))],
        ['Pending Entries', str(len([e for e in entries if e.status == 'pending']))],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 30))
    
    # Detailed entries table
    if entries:
        data = [['Time', 'Visitor', 'Phone', 'Resident', 'Purpose', 'Status']]
        
        for entry in entries:
            resident_name = 'Walk-in'
            if entry.visit_request and entry.visit_request.resident:
                resident_name = f"{entry.visit_request.resident.first_name} {entry.visit_request.resident.last_name}"
            
            purpose = entry.visit_request.purpose if entry.visit_request else 'Walk-in Visit'
            if len(purpose) > 20:
                purpose = purpose[:17] + '...'
            
            data.append([
                entry.entry_time.strftime('%H:%M'),
                entry.visitor.full_name,
                entry.visitor.phone_number,
                resident_name,
                purpose,
                entry.status.title()
            ])
        
        table = Table(data, colWidths=[0.8*inch, 1.5*inch, 1.2*inch, 1.5*inch, 1.8*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        
        elements.append(Paragraph('Detailed Entries', styles['Heading2']))
        elements.append(table)
    else:
        elements.append(Paragraph('No entries found for this date.', styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="daily_visitor_report_{report_date}.pdf"'
    
    return response

def generate_monthly_summary_excel(entries, year, month):
    """Generate monthly summary Excel report"""
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('Monthly Summary')
    
    # Define formats
    title_format = workbook.add_format({
        'bold': True,
        'font_size': 16,
        'align': 'center'
    })
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#D7E4BC',
        'border': 1
    })
    
    # Title
    worksheet.merge_range('A1:F1', f'Monthly Visitor Summary - {year}-{month:02d}', title_format)
    
    # Group entries by date
    from collections import defaultdict
    daily_stats = defaultdict(lambda: {'total': 0, 'approved': 0, 'pending': 0})
    
    for entry in entries:
        date_key = entry.entry_time.date()
        daily_stats[date_key]['total'] += 1
        if entry.status == 'approved':
            daily_stats[date_key]['approved'] += 1
        elif entry.status == 'pending':
            daily_stats[date_key]['pending'] += 1
    
    # Headers
    headers = ['Date', 'Total Entries', 'Approved', 'Pending', 'Completion Rate']
    for col, header in enumerate(headers):
        worksheet.write(3, col, header, header_format)
    
    # Data
    row = 4
    for date, stats in sorted(daily_stats.items()):
        completion_rate = (stats['approved'] / stats['total'] * 100) if stats['total'] > 0 else 0
        
        worksheet.write(row, 0, date.strftime('%Y-%m-%d'))
        worksheet.write(row, 1, stats['total'])
        worksheet.write(row, 2, stats['approved'])
        worksheet.write(row, 3, stats['pending'])
        worksheet.write(row, 4, f"{completion_rate:.1f}%")
        row += 1
    
    workbook.close()
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="monthly_summary_{year}_{month:02d}.xlsx"'
    
    return response