import heapq
from collections import deque, defaultdict
from datetime import datetime, date
import io
from matplotlib import pyplot as plt
from sqlalchemy.exc import IntegrityError
from flask import Flask, request, jsonify, render_template, redirect, send_file, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import heapq
from collections import deque, defaultdict
import networkx as nx
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your_secret_key_here'  # Required for flash messages
db = SQLAlchemy(app)

# Database Models
class Patient(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)

class Appointment(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.String(10), db.ForeignKey('staff.id'), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

class Staff(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class InventoryItem(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class BillingRecord(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    patient_id = db.Column(db.String(10), db.ForeignKey('patient.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# Hospital Management System
class HospitalManagementSystem:
    def __init__(self):
        self.graph = defaultdict(list)
        self.locations = set()
        self.appointment_heap = []
        self.graph = nx.Graph()
        self.appointment_heap = []

    def add_patient(self, patient):
        db.session.add(patient)
        db.session.commit()
        self.add_notification(f"New patient added: {patient.name}")
        return True

    def get_patient(self, patient_id):
        return Patient.query.get(patient_id)

    def update_patient(self, patient_id, updated_info):
        patient = Patient.query.get(patient_id)
        if patient:
            for key, value in updated_info.items():
                setattr(patient, key, value)
            db.session.commit()
            self.add_notification(f"Patient information updated: {patient.name}")
            return True
        return False

    def delete_patient(self, patient_id):
        patient = Patient.query.get(patient_id)
        if patient:
            db.session.delete(patient)
            db.session.commit()
            self.add_notification(f"Patient deleted: {patient.name}")
            return True
        return False

    def schedule_appointment(self, appointment):
        db.session.add(appointment)
        db.session.commit()
        heapq.heappush(self.appointment_heap, (appointment.time, appointment.id))
        self.add_notification(f"New appointment scheduled for patient ID: {appointment.patient_id}")
        return True

    def get_next_appointment(self):
        while self.appointment_heap:
            time, appointment_id = heapq.heappop(self.appointment_heap)
            appointment = Appointment.query.get(appointment_id)
            if appointment:
                return appointment
        return None

    def get_appointments(self):
        return Appointment.query.order_by(Appointment.time).all()

    def cancel_appointment(self, appointment_id):
        appointment = Appointment.query.get(appointment_id)
        if appointment:
            db.session.delete(appointment)
            db.session.commit()
            self.appointment_heap = [(time, id) for time, id in self.appointment_heap if id != appointment_id]
            heapq.heapify(self.appointment_heap)
            self.add_notification(f"Appointment cancelled for patient ID: {appointment.patient_id}")
            return True
        return False

    def add_staff(self, staff):
        db.session.add(staff)
        db.session.commit()
        self.add_notification(f"New staff member added: {staff.name}")
        return True

    def get_staff(self):
        return Staff.query.all()

    def add_inventory(self, item):
        db.session.add(item)
        db.session.commit()
        self.add_notification(f"New inventory item added: {item.name}")
        return True

    def get_inventory(self):
        return InventoryItem.query.all()

    def update_inventory(self, item_id, quantity_change):
        item = InventoryItem.query.get(item_id)
        if item:
            item.quantity += quantity_change
            db.session.commit()
            self.add_notification(f"Inventory updated for {item.name}: {quantity_change}")
            return True
        return False

    def add_billing_record(self, record):
        db.session.add(record)
        db.session.commit()
        self.add_notification(f"New billing record added for patient ID: {record.patient_id}")
        return True

    def get_billing_records(self, patient_id):
        return BillingRecord.query.filter_by(patient_id=patient_id).all()

    def add_notification(self, message):
        notification = Notification(message=message)
        db.session.add(notification)
        db.session.commit()

    def get_notifications(self):
        return Notification.query.order_by(Notification.timestamp.desc()).limit(5).all()
    
    def sort_patients_by_name(self):
        patients = Patient.query.all()
        return sorted(patients, key=lambda x: x.name)

    def binary_search_patient_by_name(self, name):
        patients = self.sort_patients_by_name()
        left, right = 0, len(patients) - 1
        while left <= right:
            mid = (left + right) // 2
            if patients[mid].name == name:
                return patients[mid]
            elif patients[mid].name < name:
                left = mid + 1
            else:
                right = mid - 1
        return None

    def add_hospital_location(self, location):
        self.graph.add_node(location)
        return True

    def add_path(self, start, end):
        if start in self.graph.nodes and end in self.graph.nodes:
            self.graph.add_edge(start, end)
            return True
        return False

    def find_path(self, start, end):
        try:
            path = nx.shortest_path(self.graph, start, end)
            return path
        except nx.NetworkXNoPath:
            return None

# Initialize the Hospital Management System
hms = HospitalManagementSystem()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/patients')
def patients():
    all_patients = Patient.query.all()
    return render_template('patients.html', patients=all_patients)

@app.route('/patient/add', methods=['GET', 'POST'])
def add_patient():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        name = request.form['name']
        age = int(request.form['age'])
        gender = request.form['gender']

        existing_patient = Patient.query.get(patient_id)
        if existing_patient:
            flash(f'A patient with ID {patient_id} already exists.', 'error')
            return render_template('add_patient.html', 
                                   prefill={'name': name, 'age': age, 'gender': gender})

        new_patient = Patient(id=patient_id, name=name, age=age, gender=gender)
        
        try:
            hms.add_patient(new_patient)
            flash('Patient added successfully!', 'success')
            return redirect(url_for('patients'))
        except IntegrityError:
            db.session.rollback()
            flash(f'An error occurred. Patient with ID {patient_id} might already exist.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
    
    return render_template('add_patient.html')

@app.route('/patients/sorted')
def sorted_patients():
    sorted_patients = hms.sort_patients_by_name()
    return render_template('sorted_patients.html', patients=sorted_patients)

@app.route('/patients/search', methods=['GET', 'POST'])
def search_patient():
    if request.method == 'POST':
        name = request.form['name']
        patient = hms.binary_search_patient_by_name(name)
        if patient:
            return render_template('patient_details.html', patient=patient)
        else:
            flash('Patient not found', 'error')
    return render_template('search_patient.html')

@app.route('/appointments')
def appointments():
    all_appointments = hms.get_appointments()
    return render_template('appointments.html', appointments=all_appointments)

@app.route('/appointment/schedule', methods=['GET', 'POST'])
def schedule_appointment():
    if request.method == 'POST':
        appointment = Appointment(
            id=request.form['appointment_id'],
            patient_id=request.form['patient_id'],
            doctor_id=request.form['doctor_id'],
            time=datetime.strptime(request.form['time'], '%Y-%m-%dT%H:%M')
        )
        success = hms.schedule_appointment(appointment)
        if success:
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments'))
        else:
            flash('Failed to schedule appointment.', 'error')
    return render_template('schedule_appointment.html')

@app.route('/appointment/cancel/<appointment_id>', methods=['POST'])
def cancel_appointment(appointment_id):
    success = hms.cancel_appointment(appointment_id)
    if success:
        flash('Appointment cancelled successfully!', 'success')
    else:
        flash('Failed to cancel appointment.', 'error')
    return redirect(url_for('appointments'))

@app.route('/staff')
def staff():
    all_staff = hms.get_staff()
    return render_template('staff.html', staff=all_staff)

@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        staff = Staff(
            id=request.form['staff_id'],
            name=request.form['name'],
            role=request.form['role']
        )
        success = hms.add_staff(staff)
        if success:
            flash('Staff member added successfully!', 'success')
            return redirect(url_for('staff'))
        else:
            flash('Failed to add staff member.', 'error')
    return render_template('add_staff.html')

@app.route('/inventory')
def inventory():
    all_items = hms.get_inventory()
    return render_template('inventory.html', items=all_items)

@app.route('/inventory/add', methods=['GET', 'POST'])
def add_inventory():
    if request.method == 'POST':
        item = InventoryItem(
            id=request.form['item_id'],
            name=request.form['name'],
            quantity=int(request.form['quantity'])
        )
        success = hms.add_inventory(item)
        if success:
            flash('Inventory item added successfully!', 'success')
            return redirect(url_for('inventory'))
        else:
            flash('Failed to add inventory item.', 'error')
    return render_template('add_inventory.html')

@app.route('/inventory/update', methods=['POST'])
def update_inventory():
    item_id = request.form['item_id']
    quantity_change = int(request.form['quantity_change'])
    success = hms.update_inventory(item_id, quantity_change)
    if success:
        flash('Inventory updated successfully!', 'success')
    else:
        flash('Failed to update inventory.', 'error')
    return redirect(url_for('inventory'))

@app.route('/billing/<patient_id>')
def billing(patient_id):
    records = hms.get_billing_records(patient_id)
    return render_template('billing.html', records=records, patient_id=patient_id)

@app.route('/billing/add', methods=['GET', 'POST'])
def add_billing():
    if request.method == 'POST':
        record = BillingRecord(
            id=request.form['record_id'],
            patient_id=request.form['patient_id'],
            amount=float(request.form['amount']),
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        )
        success = hms.add_billing_record(record)
        if success:
            flash('Billing record added successfully!', 'success')
            return redirect(url_for('billing', patient_id=record.patient_id))
        else:
            flash('Failed to add billing record.', 'error')
    return render_template('add_billing.html')

@app.route('/notifications')
def get_notifications():
    notifications = hms.get_notifications()
    return jsonify([{'message': n.message, 'timestamp': n.timestamp.isoformat()} for n in notifications])

@app.route('/navigation')
def navigation():
    return render_template('navigation.html')

@app.route('/navigation/add_location', methods=['POST'])
def add_location():
    location = request.form['location']
    success = hms.add_hospital_location(location)
    if success:
        flash('Location added successfully!', 'success')
    else:
        flash('Failed to add location. It might already exist.', 'error')
    return redirect(url_for('navigation'))

@app.route('/navigation/add_path', methods=['POST'])
def add_path():
    start = request.form['start']
    end = request.form['end']
    success = hms.add_path(start, end)
    if success:
        flash('Path added successfully!', 'success')
    else:
        flash('Failed to add path. Make sure both locations exist.', 'error')
    return redirect(url_for('navigation'))

@app.route('/navigation/visualize')
def visualize_hospital_layout():
    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(hms.graph)
    nx.draw(hms.graph, pos, with_labels=True, node_color='lightblue', node_size=500, font_size=10, font_weight='bold')
    edge_labels = nx.get_edge_attributes(hms.graph, 'weight')
    nx.draw_networkx_edge_labels(hms.graph, pos, edge_labels=edge_labels)
    
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    
    return send_file(img, mimetype='image/png')


@app.route('/navigation/find_path', methods=['POST'])
def find_path():
    start = request.form['start']
    end = request.form['end']
    path = hms.find_path(start, end)
    if path:
        return jsonify({'path': path})
    else:
        return jsonify({'error': 'No path found'}), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
