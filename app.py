from flask import Flask, render_template, request, send_file
import json
from datetime import datetime
import openpyxl
from openpyxl import Workbook
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# Sample hostel and student data (edit this with your actual 50 students per hostel)
students_data = {
    'Hostel 1': [f'Student_{i}' for i in range(1, 51)],
    'Hostel 2': [f'Student_{i}' for i in range(51, 101)],
    'Hostel 3': [f'Student_{i}' for i in range(101, 151)],
    'Hostel 4': [f'Student_{i}' for i in range(151, 201)],
    'Hostel 5': [f'Student_{i}' for i in range(201, 251)]
}


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        hostel = request.form['hostel']
        attendance = {}
        for student in students_data[hostel]:
            status = 'Present' if f'present_{student}' in request.form else 'Absent'
            attendance[student] = status

        # Get current date and time
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H_%M_%S')  # Replace colons with underscores for valid file name

        # Sanitize hostel name (replace spaces with underscores)
        safe_hostel = hostel.replace(' ', '_')
        # Generate PDF with sanitized file name
        pdf_file = f'attendance_{safe_hostel}{date_str}{time_str}.pdf'
        pdf_path = os.path.join(os.getcwd(), pdf_file)

        pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Attendance Report - {hostel}", styles['Heading1']))
        story.append(Paragraph(f"Date: {date_str} | Time: {time_str.replace('_', ':')}", styles['Normal']))
        story.append(Spacer(1, 12))

        for student, status in attendance.items():
            story.append(Paragraph(f"{student}: {status}", styles['Normal']))

        pdf.build(story)

        # Return template with download link
        return render_template('index.html',
                               hostels=list(students_data.keys()),
                               students_json=json.dumps(students_data),
                               pdf_url=pdf_file,
                               message='Attendance submitted successfully! Download the PDF below.')

    # For GET request: Render the form
    return render_template('index.html',
                           hostels=list(students_data.keys()),
                           students_json=json.dumps(students_data))


@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)