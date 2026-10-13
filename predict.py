
import joblib
from pathlib import Path

from database import (
    initialize_database,
    save_complaint,
    get_complaints
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "civicpulse_model.pkl"

# Load the trained ML model
if not MODEL_PATH.exists():
    print("Model not found. Run train_model.py first.")
    raise SystemExit(1)

model = joblib.load(MODEL_PATH)

# Create the database table if necessary
initialize_database()

print("=" * 45)
print("          CIVICPULSE AI")
print("   Smart City Complaint Management")
print("=" * 45)

while True:
    print("\nOptions: Submit a complaint | history | exit")

    command = input("\nEnter your choice: ").strip()

    if command.lower() == "exit":
        print("Thank you for using CivicPulse AI!")
        break

    # Display previously saved complaints
    if command.lower() == "history":
        records = get_complaints()

        if not records:
            print("No complaints have been saved yet.")
        else:
            print("\n========== COMPLAINT HISTORY ==========")

            for record in records:
                complaint_id, city, text, category, status, created_at = record

                print(f"\nID: {complaint_id}")
                print(f"City: {city}")
                print(f"Complaint: {text}")
                print(f"Category: {category}")
                print(f"Status: {status}")
                print(f"Created at: {created_at}")

        continue

    # Collect a new complaint
    city = input("Enter your city: ").strip()

    if not city:
        print("City cannot be empty.")
        continue

    complaint = input("Enter your complaint: ").strip()

    if not complaint:
        print("Complaint cannot be empty.")
        continue

    # Predict its category
    category = model.predict([complaint])[0]

    # Save it in SQLite
    complaint_id = save_complaint(
        city,
        complaint,
        category
    )

    print("\n========== COMPLAINT SAVED ==========")
    print("Complaint ID:", complaint_id)
    print("City:", city)
    print("Complaint:", complaint)
    print("Predicted category:", category)
    print("Status: Submitted")
    print("Record saved successfully!")
