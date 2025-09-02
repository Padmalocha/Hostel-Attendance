from flask import Flask, render_template, request, send_file
import json
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import pytz  # Added for time zone support

app = Flask(__name__)

# Sample hostel and student data (unchanged)
students_data = {
'Hostels':[],
    'Hostel 1': [
        "Dushmanta Sabar",
        "Jubraj Naik",
        "Pradeep Dharua",
        "Aroprakash Barik",
        "Kanha Bauri",
        "Rituraj Biswal",
        "Bibhrat Biswal",
        "Likun Das",
        "Manas Rout",
        "Jeebanjyoti Bhuyan",
        "Diptiranjan Dalai",
        "Nirdosh Xess",
        "Pradeep Nayak",
        "Sunil Tandi",
        "Jitu Soren",
        "Saroj Barha",
        "Sekhar Chandra Naik",
        "Basudev Naik",
        "Dharmendra Naik",
        "Nikhilkumar Pattnayak",
        "Pradeepkumar Bhatra",
        "Chandrachuda Srichandan",
        "Bharatkumar Majhi",
        "Prasant Pradhan",
        "Nibasis Naik",
        "Bhagatram Tanti",
        "Sandeep Sethy",
        "Lambodhar Hansda",
        "Umeshcharana Rana",
        "Kedarkumar Rour",
        "Sansadhar Mana",
        "Chandra Hansdah",
        "Manoj Maharana",
        "Asish Behera",
        "Pyushkumar Khara"
    ],
    'Hostel 2': [f'Student_{i}' for i in range(51, 101)],
    'Hostel 3': [f'Student_{i}' for i in range(101, 151)],
    'Hostel 4': [f'Student_{i}' for i in range(151, 201)],
    'Hostel 5': [f'Student_{i}' for i in range(201, 251)],
    'Hostel 6': [f'Student_{i}' for i in range(251, 301)]
}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        hostel = request.form['hostel']
        attendance = {}
        for student in students_data[hostel]:
            status = 'Present' if f'present_{student}' in request.form else 'Absent'
            attendance[student] = status

        # Get current date and time in IST
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        date_str = now.strftime('%Y-%m-%d')  # e.g., 2025-09-02
        time_str = now.strftime('%H_%M_%S')  # For filename: e.g., 07_20_45
        display_time_str = now.strftime('%I:%M:%S %p')  # For PDF display: e.g., 07:20:45 AM

        # Sanitize hostel name (replace spaces with underscores)
        safe_hostel = hostel.replace(' ', '_')
        # Generate PDF with sanitized file name
        pdf_file = f'attendance_{safe_hostel}{date_str}{time_str}.pdf'
        pdf_path = os.path.join(os.getcwd(), pdf_file)

        # Count present and absent students
        present_count = sum(1 for status in attendance.values() if status == "Present")
        absent_count = sum(1 for status in attendance.values() if status == "Absent")

        pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"Attendance Report - {hostel}", styles['Heading1']))
        story.append(Paragraph(''))
        story.append(Paragraph(f"Date: {date_str} | Time: {display_time_str}", styles['Normal']))  # Updated time format
        story.append(Spacer(1, 12))

        # Add summary counts
        story.append(Paragraph(f"Total Students: {len(attendance)}", styles['Normal']))
        story.append(Paragraph(f"Present: {present_count}", styles['Normal']))
        story.append(Paragraph(f"Absent: {absent_count}", styles['Normal']))
        story.append(Paragraph(''))
        story.append(Spacer(1, 12))

        # Add student-wise details
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