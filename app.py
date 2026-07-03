from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, db, auth
from datetime import datetime
import os
import json

app = Flask(__name__)
CORS(app)

# ---------------- Firebase Init ----------------
if not firebase_admin._apps:

    if os.path.exists("serviceAccountKey.json"):
        # Local computer
        cred = credentials.Certificate("serviceAccountKey.json")
    else:
        # Render
        firebase_json = json.loads(os.environ["FIREBASE_CREDENTIALS"])
        cred = credentials.Certificate(firebase_json)

    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://hospital-57fc8-default-rtdb.firebaseio.com"
    })


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login-page")
def login_page():
    return render_template("login.html")


@app.route("/payment")
def payment():
    return render_template("payment.html")


@app.route("/temp-dash")
def temp_dash():
    return render_template("temp-dash.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ---------------- LOGIN API ----------------
@app.route("/login", methods=["POST"])
def login():
    try:
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "No token"}), 401

        token = token.replace("Bearer ", "")
        decoded = auth.verify_id_token(token)

        uid = decoded["uid"]
        hospital = db.reference(f"hospitals/{uid}").get() or {}

        return jsonify({
            "uid": uid,
            "hospitalId": hospital.get("hospitalId", ""),
            "hospitalName": hospital.get("hospital_name", "")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 401


# ---------------- SAVE HOSPITAL ----------------
@app.route("/save_hospital", methods=["POST"])
def save_hospital():
    uid = request.form.get("uid")

    if not uid:
        return jsonify({"error": "UID missing"}), 400

    names = request.form.getlist("doctor_name")
    specs = request.form.getlist("specialization")
    times = request.form.getlist("opd_time")
    infos = request.form.getlist("doctor_info")

    doctors = []
    for i in range(min(len(names), len(specs), len(times), len(infos))):
        doctors.append({
            "doctor_name": names[i],
            "specialization": specs[i],
            "opd_time": times[i],
            "doctor_info": infos[i]
        })

    hospital_data = {
        "uid": uid,
        "hospital_name": request.form.get("hospital_name"),
        "date": request.form.get("date"),
        "open_time": request.form.get("open_time"),
        "close_time": request.form.get("close_time"),
        "info": request.form.get("info"),
        "created_at": str(datetime.now()),
        "doctors": doctors
    }

    db.reference("hospitals").child(uid).set(hospital_data)

    return jsonify({"message": "Saved", "uid": uid})


# ---------------- HOSPITAL PAGE ----------------
@app.route("/hospital/<uid>")
def hospital_page(uid):
    data = db.reference(f"hospitals/{uid}").get()
    return render_template("hospital.html", hospital=data, uid=uid)


# ---------------- BOOK PAGE ----------------
@app.route("/hospital/<uid>/book")
def book_page(uid):
    hospital = db.reference(f"hospitals/{uid}").get()
    return render_template("appointment.html", hospital=hospital, uid=uid)


# ---------------- BOOK APPOINTMENT ----------------
@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    hospital_id = request.form.get("hospital_id")

    if not hospital_id:
        return jsonify({"error": "Hospital ID missing"}), 400

    counter_ref = db.reference("counters/patient_no")
    current = counter_ref.get() or 0
    patient_no = current + 1
    counter_ref.set(patient_no)

    appointment = {
        "hospital_id": hospital_id,
        "patient_no": patient_no,
        "doctor_name": request.form.get("doctor_name"),
        "patient_name": request.form.get("patient_name"),
        "gender": request.form.get("gender"),
        "age": request.form.get("age"),
        "mobile": request.form.get("mobile"),
        "address": request.form.get("address"),
        "appointment_date": request.form.get("appointment_date"),
        "created_at": str(datetime.now())
    }

    db.reference("appointments").push(appointment)

    return render_template("success.html")


# ---------------- APPOINTMENTS LIST ----------------
@app.route("/appointments/<uid>")
def appointments(uid):
    data = db.reference("appointments").get() or {}
    grouped = {}

    for _, patient in data.items():
        date = patient.get("appointment_date", "Unknown")
        grouped.setdefault(date, []).append(patient)

    return render_template("appointments.html", grouped=grouped)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)

