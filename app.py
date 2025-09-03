from flask import Flask, render_template, request, redirect, url_for, session, Response, send_file
import os, cv2, face_recognition, numpy as np
from datetime import datetime
import pytz
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from google.cloud import firestore, storage
from google.oauth2 import service_account
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Google Cloud
credentials = service_account.Credentials.from_service_account_file("key.json")
db = firestore.Client(credentials=credentials, project=credentials.project_id)
storage_client = storage.Client(credentials=credentials, project=credentials.project_id)
bucket_name = "your-bucket-name"   # Replace with your GCS bucket
bucket = storage_client.bucket(bucket_name)

# Dummy login (replace with Firestore users later)
users = {"user": "password"}
admins = {"admin": "admin123"}

# Hostel Data
hostels = ["Hostel 1", "Hostel 2", "Hostel 3", "Hostel 4"]

# Face folder
FACE_FOLDER = "faces"
os.makedirs(FACE_FOLDER, exist_ok=True)

# ---------------- HELPERS ----------------
def load_known_faces():
    encodings, names = [], []
    for filename in os.listdir(FACE_FOLDER):
        if filename.endswith(".jpg") or filename.endswith(".png"):
            img = face_recognition.load_image_file(os.path.join(FACE_FOLDER, filename))
            enc = face_recognition.face_encodings(img)
            if enc:
                encodings.append(enc[0])
                names.append(filename.split(".")[0])
    return encodings, names
def generate_pdf(records, hostel_name, date_str):
    """Generate PDF report locally"""
    pdf_filename = f"attendance_{hostel_name}_{date_str}.pdf"
    pdf_path = os.path.join(os.getcwd(), pdf_filename)

    pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Attendance Report - {hostel_name}", styles['Heading1']))
    story.append(Paragraph(f"Date: {date_str}", styles['Normal']))
    story.append(Spacer(1, 12))

    for record in records:
        story.append(Paragraph(
            f"Name: {record.get('name','N/A')} | "
            f"Status: {record.get('status','Unknown')} | "
            f"Time: {record.get('time','')}", styles['Normal']
        ))

    pdf.build(story)

    return pdf_path

# ---------------- ROUTES ----------------
from flask import send_file

@app.route("/admin/download/<hostel>/<date>")
def download_pdf(hostel, date):
    docs = db.collection("attendance").where("hostel", "==", hostel).where("date", "==", date).stream()
    records = [doc.to_dict() for doc in docs]

    if not records:
        return f"No records found for {hostel} on {date}", 404

    pdf_path = generate_pdf(records, hostel, date)
    return send_file(pdf_path, as_attachment=True)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users[username] == password:
            session["user"] = username
            return redirect(url_for("user_dashboard"))
        elif username in admins and admins[username] == password:
            session["admin"] = username
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")



@app.route("/user_dashboard")
def user_dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("user_dashboard.html", hostels=hostels)



# ---------------- REGISTER STUDENT ----------------
@app.route("/register/<hostel>", methods=["GET", "POST"])
def register_student(hostel):
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        department = request.form["department"]
        gender = request.form["gender"]

        # Open webcam
        camera = cv2.VideoCapture(0)
        success, frame = camera.read()
        camera.release()

        if success:
            # Convert to bytes for upload
            _, buffer = cv2.imencode(".jpg", frame)
            image_bytes = buffer.tobytes()

            # Upload image to GCS
            filename = f"{hostel}_{name}.jpg"
            blob = bucket.blob(f"faces/{filename}")
            blob.upload_from_string(image_bytes, content_type="image/jpeg")
            image_url = blob.public_url

            # Encode face
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, face_locations)

            if encodings:
                encoding_list = encodings[0].tolist()

                # Save student record in Firestore
                db.collection("students").add({
                    "name": name,
                    "department": department,
                    "gender": gender,
                    "hostel": hostel,
                    "image_url": image_url,  # ✅ store photo link
                    "encoding": encoding_list,
                    "registered": True
                })

                return render_template("register_form.html",
                                       hostel=hostel,
                                       message="✅ Student registered successfully!")
            else:
                return render_template("register_form.html",
                                       hostel=hostel,
                                       message="❌ No face detected. Try again.")
        else:
            return render_template("register_form.html",
                                   hostel=hostel,
                                   message="❌ Failed to open camera.")

    return render_template("register_form.html", hostel=hostel)

# ---------------- ATTENDANCE ----------------
# ---------------- ATTENDANCE ----------------
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if "user" not in session:
        return redirect(url_for("login"))

    students = []
    selected_hostel = None

    if request.method == "POST":
        hostel = request.form["hostel"]
        selected_hostel = hostel

        # 🔎 Fetch students of this hostel from Firestore
        docs = db.collection("students").where("hostel", "==", hostel).stream()
        students = [doc.to_dict() for doc in docs]

    return render_template("attendance.html",
                           hostels=hostels,
                           students=students,
                           selected_hostel=selected_hostel,
                           recognized=None)


@app.route("/attendance/<hostel>/<student_name>")
def mark_attendance(hostel, student_name):
    if "user" not in session:
        return redirect(url_for("login"))

    recognized_msg = "❌ Face not recognized"

    # 🔎 Fetch encodings of students from Firestore
    docs = db.collection("students").where("hostel", "==", hostel).stream()
    known_encodings, known_names = [], []
    for doc in docs:
        student = doc.to_dict()
        if "encoding" in student:
            known_encodings.append(np.array(student["encoding"]))
            known_names.append(student["name"])

    # ✅ Auto-detect webcam
    camera = cv2.VideoCapture(0)
    frame = None
    for i in range(30):
        success, temp_frame = camera.read()
        if not success:
            continue
        rgb = cv2.cvtColor(temp_frame, cv2.COLOR_BGR2RGB)
        if face_recognition.face_locations(rgb):
            frame = temp_frame
            break
    camera.release()

    if frame is not None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = face_recognition.face_encodings(rgb)

        for face_encoding in faces:
            matches = face_recognition.compare_faces(known_encodings, face_encoding)
            face_distances = face_recognition.face_distance(known_encodings, face_encoding)

            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    matched_name = known_names[best_match_index]
                    if matched_name == student_name:
                        # ✅ Mark attendance
                        ist = pytz.timezone("Asia/Kolkata")
                        now = datetime.now(ist)
                        date_str, time_str = now.strftime("%Y-%m-%d"), now.strftime("%I:%M %p")

                        existing = db.collection("attendance") \
                                     .where("name", "==", student_name) \
                                     .where("date", "==", date_str).stream()

                        if not list(existing):
                            db.collection("attendance").add({
                                "name": student_name,
                                "hostel": hostel,
                                "date": date_str,
                                "time": time_str,
                                "status": "Present"
                            })
                        recognized_msg = f"✅ {student_name} marked Present!"
                    else:
                        recognized_msg = "❌ Face does not match this student"
    else:
        recognized_msg = "❌ No face detected. Try again."

    return render_template("attendance.html",
                           hostels=hostels,
                           students=[],
                           selected_hostel=None,
                           recognized=recognized_msg)



# ---------------- ADMIN ----------------
@app.route("/admin_dashboard", methods=["GET", "POST"])
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("login"))

    records = db.collection("attendance").stream()
    data = [r.to_dict() for r in records]
    return render_template("admin_dashboard.html", records=data, hostels=hostels)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True) 