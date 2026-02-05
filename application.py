from flask import Flask, request, jsonify
from pymongo import MongoClient, ReturnDocument
from datetime import datetime, timedelta, timezone
import certifi
import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ---------- 🔗 MONGODB CONNECTION ----------
print("🔗 Connecting to MongoDB...")
MONGO_ATLAS = os.getenv('MONGO_ATLAS_URI', 'mongodb://localhost:27017/')
print(f"🌐 Using: {'ATLAS' if 'mongodb+srv' in MONGO_ATLAS else 'LOCAL MongoDB'}")

try:
    tls_params = {'tlsCAFile': certifi.where()} if 'mongodb+srv' in MONGO_ATLAS else {}
    client = MongoClient(MONGO_ATLAS, **tls_params, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ Connected to MongoDB!")
    ATLAS_CONNECTED = True
except Exception as e:
    print(f"❌ Atlas failed: {e}")
    print("🔄 Falling back to LOCAL MongoDB...")
    client = MongoClient('mongodb://localhost:27017/')
    client.admin.command('ping')
    print("✅ Connected to LOCAL MongoDB!")
    ATLAS_CONNECTED = False

db = client["smart_parking"]
users_collection = db["users"]
bookings_collection = db["bookings"]
slots_collection = db["parking_slots"]

# ---------- LOAD & SAVE STAFF DATABASE ----------
def load_staff_database():
    """Load staff database from JSON"""
    try:
        with open('staff_database.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ staff_database.json not found!")
        default_db = {
            "CSE": {"cse101": {"registered": False}},
            "ECE": {"ece101": {"registered": False}}
        }
        with open('staff_database.json', 'w') as f:
            json.dump(default_db, f, indent=2)
        return default_db
    except Exception as e:
        print(f"❌ Error loading staff database: {e}")
        return {}

def save_staff_database(data):
    """Save updated staff database to JSON file"""
    try:
        with open('staff_database.json', 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving staff database: {e}")
        return False

# ---------- LOAD & SAVE STUDENT DATABASE ----------
def load_student_database():
    """Load student database from JSON"""
    try:
        with open('student_database.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ student_database.json not found!")
        default_db = {
            "CSE": {"cse21001": {"registered": False}},
            "ECE": {"ece21001": {"registered": False}}
        }
        with open('student_database.json', 'w') as f:
            json.dump(default_db, f, indent=2)
        return default_db
    except Exception as e:
        print(f"❌ Error loading student database: {e}")
        return {}

def save_student_database(data):
    """Save updated student database to JSON file"""
    try:
        with open('student_database.json', 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving student database: {e}")
        return False

# ---------- CHECK STAFF ID ----------
def check_staff_id(staff_id):
    """
    Check if staff_id exists in database
    Returns: (exists, department, is_registered)
    """
    staff_db = load_staff_database()
    staff_id_lower = staff_id.lower()
    
    for department, staff_list in staff_db.items():
        if staff_id_lower in staff_list:
            is_registered = staff_list[staff_id_lower].get("registered", False)
            return True, department, is_registered
    
    return False, None, False

def mark_staff_registered(staff_id):
    """Mark staff member as registered in JSON database"""
    staff_db = load_staff_database()
    staff_id_lower = staff_id.lower()
    
    for department, staff_list in staff_db.items():
        if staff_id_lower in staff_list:
            staff_db[department][staff_id_lower]["registered"] = True
            return save_staff_database(staff_db)
    
    return False

# ---------- CHECK STUDENT ID ----------
def check_student_id(student_id):
    """
    Check if student_id exists in database
    Returns: (exists, department, is_registered)
    """
    student_db = load_student_database()
    student_id_lower = student_id.lower()
    
    for department, student_list in student_db.items():
        if student_id_lower in student_list:
            is_registered = student_list[student_id_lower].get("registered", False)
            return True, department, is_registered
    
    return False, None, False

def mark_student_registered(student_id):
    """Mark student as registered in JSON database"""
    student_db = load_student_database()
    student_id_lower = student_id.lower()
    
    for department, student_list in student_db.items():
        if student_id_lower in student_list:
            student_db[department][student_id_lower]["registered"] = True
            return save_student_database(student_db)
    
    return False

# ---------- VALIDATION FUNCTIONS ----------
def validate_email(email):
    if not email or len(email) < 7 or len(email) > 99:
        return False
    try:
        parts = email.split('@')
        return len(parts) == 2 and '.' in parts[1]
    except:
        return False

def validate_password(password):
    return len(password) == 6 and password.isdigit()

# ---------- INIT PARKING SLOTS ----------
def init_slots():
    if slots_collection.count_documents({}) == 0:
        slots = [{"slot_id": f"S{i}", "available": True, "reserved_by": None} for i in range(1, 6)]
        slots_collection.insert_many(slots)
        print("✅ 5 Parking slots initialized!")

init_slots()

# Load databases
staff_db = load_staff_database()
student_db = load_student_database()
total_staff = sum(len(staff_list) for staff_list in staff_db.values())
total_students = sum(len(student_list) for student_list in student_db.values())
print(f"✅ Loaded {total_staff} staff from {len(staff_db)} departments")
print(f"✅ Loaded {total_students} students from {len(student_db)} departments")

# ---------- 1. REGISTER WITH STAFF & STUDENT VERIFICATION ✅ ----------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json or {}
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")
    user_type = data.get("user_type")  # "student" or "staff"
    user_id_input = data.get("staff_id", "").strip() or data.get("student_id", "").strip()
    
    # VALIDATIONS
    if not validate_email(email):
        return jsonify({"success": False, "error": "❌ Invalid email format"}), 400
    
    if not validate_password(password):
        return jsonify({"success": False, "error": "❌ Password must be 6 digits numeric"}), 400
    
    if password != confirm_password:
        return jsonify({"success": False, "error": "❌ Passwords don't match"}), 400
    
    if users_collection.find_one({"email": email}):
        return jsonify({"success": False, "error": "❌ Email already registered"}), 400
    
    # VERIFICATION BASED ON USER TYPE
    department = None
    final_user_id = None
    
    if user_type == "staff":
        # STAFF VERIFICATION
        if not user_id_input:
            return jsonify({"success": False, "error": "❌ Staff ID required"}), 400
        
        exists, dept, is_registered = check_staff_id(user_id_input)
        
        if not exists:
            return jsonify({
                "success": False, 
                "error": f"❌ Staff ID '{user_id_input}' not found in database"
            }), 400
        
        if is_registered:
            return jsonify({
                "success": False, 
                "error": f"❌ Staff ID '{user_id_input}' is already registered"
            }), 400
        
        department = dept
        final_user_id = user_id_input
        
    elif user_type == "student":
        # STUDENT VERIFICATION
        if not user_id_input:
            return jsonify({"success": False, "error": "❌ Student ID required"}), 400
        
        exists, dept, is_registered = check_student_id(user_id_input)
        
        if not exists:
            return jsonify({
                "success": False, 
                "error": f"❌ Student ID '{user_id_input}' not found in database"
            }), 400
        
        if is_registered:
            return jsonify({
                "success": False, 
                "error": f"❌ Student ID '{user_id_input}' is already registered"
            }), 400
        
        department = dept
        final_user_id = user_id_input
    
    else:
        return jsonify({"success": False, "error": "❌ Invalid user type"}), 400
    
    # CREATE USER IN MONGODB
    user_data = {
        "email": email,
        "password": generate_password_hash(password),
        "user_type": user_type,
        "staff_id": final_user_id if user_type == "staff" else None,
        "student_id": final_user_id if user_type == "student" else None,
        "department": department,
        "created_at": datetime.now(timezone.utc),
        "is_active": True
    }
    
    user_id = users_collection.insert_one(user_data).inserted_id
    
    # MARK AS REGISTERED IN JSON DATABASE
    if user_type == "staff":
        if mark_staff_registered(final_user_id):
            print(f"✅ Marked {final_user_id} as registered in staff_database.json")
    elif user_type == "student":
        if mark_student_registered(final_user_id):
            print(f"✅ Marked {final_user_id} as registered in student_database.json")
    
    return jsonify({
        "success": True,
        "message": "✅ Registration successful!",
        "user_id": str(user_id),
        "user_type": user_type,
        "staff_id": final_user_id if user_type == "staff" else None,
        "student_id": final_user_id if user_type == "student" else None,
        "department": department,
        "email": email
    }), 201

# ---------- 2. FORGOT PASSWORD ----------
@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.json or {}
    email = data.get("email", "").strip()
    
    if not validate_email(email):
        return jsonify({"success": False, "error": "❌ Invalid email"}), 400
    
    user = users_collection.find_one({"email": email, "is_active": True})
    if not user:
        return jsonify({"success": False, "error": "❌ Email not found"}), 404
    
    # SIMULATE SENDING EMAIL
    email_message = f"""
    Subject: Password Reset Request
    
    Hello,
    
    You requested to reset your password for your Smart Parking account.
    
    Please choose any 6-digit number as your new password and enter it in the app.
    
    Example: 123456, 458912, 999888, etc.
    
    Then return to the app and enter:
    - Your email: {email}
    - Your new 6-digit password
    
    If you did not request this, please ignore this email.
    
    Best regards,
    Smart Parking Team
    """
    
    print("=" * 60)
    print("📧 EMAIL SENT TO:", email)
    print(email_message)
    print("=" * 60)
    
    return jsonify({
        "success": True,
        "message": "✅ Instructions sent to your email!",
        "email": email,
        "instruction": "Check your email and choose a 6-digit number as your new password"
    })

# ---------- 3. RESET PASSWORD ----------
@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.json or {}
    email = data.get("email", "").strip()
    new_password = data.get("new_password", "")
    
    if not validate_email(email):
        return jsonify({"success": False, "error": "❌ Invalid email"}), 400
    
    if not validate_password(new_password):
        return jsonify({"success": False, "error": "❌ New password must be 6 digits"}), 400
    
    result = users_collection.update_one(
        {"email": email, "is_active": True},
        {"$set": {"password": generate_password_hash(new_password)}}
    )
    
    if result.modified_count == 0:
        return jsonify({"success": False, "error": "❌ User not found"}), 404
        
    return jsonify({
        "success": True,
        "message": "✅ Password reset successful! You can now login with your new password.",
        "email": email
    })

# ---------- 4. LOGIN ----------
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password")
    
    user = users_collection.find_one({"email": email, "is_active": True})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"success": False, "error": "❌ Invalid email/password"}), 401
    
    token = f"jwt_{str(user['_id'])}_{int(datetime.now(timezone.utc).timestamp())}"
    
    return jsonify({
        "success": True,
        "message": "✅ Login successful",
        "token": token,
        "user": {
            "email": user["email"],
            "user_type": user["user_type"],
            "staff_id": user.get("staff_id"),
            "student_id": user.get("student_id"),
            "department": user.get("department"),
            "username": user["email"].split("@")[0]
        }
    })

# ---------- 5. RESERVE SLOT (STAFF ONLY) ----------
@app.route("/auth/reserve-slot", methods=["POST"])
def reserve_slot():
    data = request.json or {}
    staff_id = data.get("staff_id")
    
    user = users_collection.find_one({"staff_id": staff_id, "user_type": "staff", "is_active": True})
    if not user:
        return jsonify({"success": False, "error": "❌ Staff access only"}), 403
    
    now = datetime.now(timezone.utc)
    slot = slots_collection.find_one_and_update(
        {"available": True, "reserved_by": None},
        {"$set": {
            "available": False,
            "reserved_by": staff_id,
            "staff_email": user["email"],
            "department": user.get("department"),
            "reservation_time": now,
            "last_updated": now
        }},
        return_document=ReturnDocument.AFTER
    )
    
    if not slot:
        return jsonify({"success": False, "error": "❌ No slots available"}), 404
    
    expires_at = now + timedelta(minutes=10)
    
    bookings_collection.insert_one({
        "staff_id": staff_id,
        "staff_email": user["email"],
        "department": user.get("department"),
        "slot_id": slot["slot_id"],
        "reserved_at": now,
        "expires_at": expires_at
    })
    
    return jsonify({
        "success": True,
        "message": "✅ Slot reserved!",
        "slot_id": slot["slot_id"],
        "staff_id": staff_id,
        "staff_email": user["email"],
        "department": user.get("department"),
        "reserved_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "duration_minutes": 10,
        "auto_refresh": True
    }), 201

# ---------- 6. MY BOOKINGS ----------
@app.route("/auth/my-bookings/<staff_id>")
def my_bookings(staff_id):
    bookings = list(bookings_collection.find(
        {"staff_id": staff_id},
        {"_id": 0}
    ).sort("reserved_at", -1).limit(20))
    
    return jsonify({
        "success": True,
        "staff_id": staff_id,
        "bookings": bookings,
        "total_bookings": len(bookings)
    })

# ---------- 7. SLOTS STATUS WITH AUTO-EXPIRE ----------
@app.route("/auth/slots_status")
def slots_status():
    slots = list(slots_collection.find({}, {"_id": 0}).sort("slot_id", 1))
    now = datetime.now(timezone.utc)
    
    for slot in slots:
        if slot.get("reservation_time"):
            expiry = slot["reservation_time"] + timedelta(minutes=10)
            total_seconds = int((expiry - now).total_seconds())
            
            if total_seconds > 0:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                slot["time_left_min"] = minutes
                slot["time_left_sec"] = seconds
                slot["countdown"] = f"{minutes:02d}:{seconds:02d}"
                slot["status"] = "RESERVED"
                slot["expires_at"] = expiry.isoformat()
                
                # Get user info if not already in slot
                if not slot.get("staff_email"):
                    user = users_collection.find_one({"staff_id": slot.get("reserved_by")})
                    if user:
                        slot["staff_email"] = user["email"]
                        slot["department"] = user.get("department")
            else:
                # AUTO-RELEASE EXPIRED SLOTS
                slots_collection.update_one(
                    {"slot_id": slot["slot_id"]},
                    {"$set": {
                        "available": True,
                        "reserved_by": None,
                        "staff_email": None,
                        "department": None,
                        "reservation_time": None
                    }}
                )
                slot["status"] = "AVAILABLE"
                if "reservation_time" in slot: del slot["reservation_time"]
                if "reserved_by" in slot: del slot["reserved_by"]
                if "staff_email" in slot: del slot["staff_email"]
                if "department" in slot: del slot["department"]
        else:
            slot["status"] = "AVAILABLE"
    
    return jsonify({
        "success": True,
        "slots": slots,
        "total_slots": len(slots),
        "total_available": len([s for s in slots if s.get("status") == "AVAILABLE"]),
        "total_reserved": len([s for s in slots if s.get("status") == "RESERVED"]),
        "timestamp": now.isoformat(),
        "auto_refresh": True,
        "refresh_interval": 1000
    })

# ---------- 8. HARDWARE ESP32 ENDPOINTS ----------
@app.route("/hardware/sensor-update", methods=["POST"])
def hardware_sensor():
    """ESP32 sends parking sensor data"""
    data = request.json or {}
    slot_id = data.get("slot_id")
    occupied = data.get("occupied", False)
    
    if not slot_id:
        return jsonify({"success": False, "error": "slot_id required"}), 400
    
    result = slots_collection.update_one(
        {"slot_id": slot_id},
        {"$set": {
            "hardware_occupied": occupied,
            "last_sensor_update": datetime.now(timezone.utc)
        }}
    )
    
    return jsonify({
        "success": True,
        "slot_id": slot_id,
        "occupied": occupied,
        "updated": result.modified_count > 0
    })

@app.route("/hardware/reserve-signal", methods=["GET"])
def esp32_reserve_status():
    """ESP32 polls this to get all slot reservation status"""
    slots = list(slots_collection.find({}, {"_id": 0}).sort("slot_id", 1))
    now = datetime.now(timezone.utc)
    
    esp32_slots = []
    
    for slot in slots:
        esp32_slot = {
            "slot_id": slot["slot_id"],
            "available": slot.get("available", True),
            "hardware_occupied": slot.get("hardware_occupied", False)
        }
        
        if slot.get("reservation_time"):
            expiry = slot["reservation_time"] + timedelta(minutes=10)
            total_seconds = int((expiry - now).total_seconds())
            
            if total_seconds > 0:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                esp32_slot.update({
                    "status": "RESERVED",
                    "reserved_by": slot.get("reserved_by"),
                    "staff_email": slot.get("staff_email"),
                    "department": slot.get("department"),
                    "time_left_min": minutes,
                    "time_left_sec": seconds,
                    "countdown": f"{minutes:02d}:{seconds:02d}",
                    "led_color": "GREEN",
                    "buzzer": False
                })
            else:
                # Expired - auto release
                slots_collection.update_one(
                    {"slot_id": slot["slot_id"]},
                    {"$set": {
                        "available": True,
                        "reserved_by": None,
                        "staff_email": None,
                        "department": None,
                        "reservation_time": None
                    }}
                )
                esp32_slot.update({
                    "status": "AVAILABLE",
                    "led_color": "OFF",
                    "buzzer": False
                })
        else:
            esp32_slot.update({
                "status": "AVAILABLE",
                "led_color": "OFF",
                "buzzer": False
            })
        
        esp32_slots.append(esp32_slot)
    
    return jsonify({
        "success": True,
        "server_ip": request.host,
        "timestamp": now.isoformat(),
        "total_slots": len(esp32_slots),
        "slots": esp32_slots,
        "refresh_rate": 1000
    })

# ---------- 9. VIEW STAFF LIST (ADMIN/DEBUG) ----------
@app.route("/auth/staff-list", methods=["GET"])
def staff_list():
    """View all staff from MongoDB (actual registered users)"""
    staff_users = list(users_collection.find(
        {"user_type": "staff", "is_active": True},
        {"_id": 0, "password": 0}
    ).sort("created_at", -1))
    
    return jsonify({
        "success": True,
        "total_staff": len(staff_users),
        "staff": staff_users,
        "source": "MongoDB users_collection"
    })

# ---------- 10. VIEW STUDENT LIST (ADMIN/DEBUG) ----------
@app.route("/auth/student-list", methods=["GET"])
def student_list():
    """View all students from MongoDB (actual registered users)"""
    student_users = list(users_collection.find(
        {"user_type": "student", "is_active": True},
        {"_id": 0, "password": 0}
    ).sort("created_at", -1))
    
    return jsonify({
        "success": True,
        "total_students": len(student_users),
        "students": student_users,
        "source": "MongoDB users_collection"
    })

# ---------- 11. CHECK STAFF ID (UTILITY) ----------
@app.route("/auth/check-staff/<staff_id>", methods=["GET"])
def check_staff(staff_id):
    """Check if staff ID exists in JSON database and registration status"""
    exists, department, is_registered = check_staff_id(staff_id)
    
    if not exists:
        return jsonify({
            "success": False,
            "exists": False,
            "message": f"Staff ID '{staff_id}' not found in database"
        }), 404
    
    return jsonify({
        "success": True,
        "exists": True,
        "staff_id": staff_id,
        "department": department,
        "registered": is_registered,
        "message": "Already registered" if is_registered else "Available for registration"
    })

# ---------- 12. CHECK STUDENT ID (UTILITY) ----------
@app.route("/auth/check-student/<student_id>", methods=["GET"])
def check_student(student_id):
    """Check if student ID exists in JSON database and registration status"""
    exists, department, is_registered = check_student_id(student_id)
    
    if not exists:
        return jsonify({
            "success": False,
            "exists": False,
            "message": f"Student ID '{student_id}' not found in database"
        }), 404
    
    return jsonify({
        "success": True,
        "exists": True,
        "student_id": student_id,
        "department": department,
        "registered": is_registered,
        "message": "Already registered" if is_registered else "Available for registration"
    })

# ---------- 13. VIEW ALL REGISTERED USERS (ADMIN) ----------
@app.route("/auth/all-users", methods=["GET"])
def all_users():
    """View all registered users (both staff and students) from MongoDB"""
    all_users_list = list(users_collection.find(
        {"is_active": True},
        {"_id": 0, "password": 0}
    ).sort("created_at", -1))
    
    staff_count = len([u for u in all_users_list if u.get("user_type") == "staff"])
    student_count = len([u for u in all_users_list if u.get("user_type") == "student"])
    
    return jsonify({
        "success": True,
        "total_users": len(all_users_list),
        "total_staff": staff_count,
        "total_students": student_count,
        "users": all_users_list,
        "source": "MongoDB users_collection"
    })

if __name__ == "__main__":
    print("🚀 Smart Parking Auth API → http://0.0.0.0:5006")
    print("=" * 70)
    print("📱 AUTHENTICATION ENDPOINTS:")
    print("   POST /auth/register              - Register (staff or student)")
    print("   POST /auth/login                 - Login")
    print("   POST /auth/forgot-password       - Request password reset")
    print("   POST /auth/reset-password        - Reset password")
    print("")
    print("🎫 PARKING RESERVATION ENDPOINTS:")
    print("   POST /auth/reserve-slot          - Reserve parking slot (staff only)")
    print("   GET  /auth/my-bookings/<staff_id> - View booking history")
    print("   GET  /auth/slots_status          - View all parking slots status")
    print("")
    print("🔧 HARDWARE ESP32 ENDPOINTS:")
    print("   POST /hardware/sensor-update     - Update sensor data")
    print("   GET  /hardware/reserve-signal    - Get reservation signals for ESP32")
    print("")
    print("👥 ADMIN/DEBUG ENDPOINTS:")
    print("   GET  /auth/staff-list            - View registered staff (MongoDB)")
    print("   GET  /auth/student-list          - View registered students (MongoDB)")
    print("   GET  /auth/all-users             - View all registered users (MongoDB)")
    print("   GET  /auth/check-staff/<id>      - Check staff ID status (JSON)")
    print("   GET  /auth/check-student/<id>    - Check student ID status (JSON)")
    print("=" * 70)
    print(f"💾 Database Status:")
    print(f"   Atlas Connected: {ATLAS_CONNECTED}")
    print(f"   Staff in JSON: {total_staff}")
    print(f"   Students in JSON: {total_students}")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5006, debug=True)