
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix
)

# ==========================================
# 1. CIVICPULSE AI: TRAINING DATASET
# ==========================================

complaints = [
    # Road Damage
    "There is a pothole on the road",
    "The road is broken and damaged",
    "Many holes are present on the street",
    "Road surface is cracked",
    "The street needs road repair",
    "A large pothole damaged my car",
    "The road has deep cracks",
    "A section of road has collapsed",
    "The pavement is badly damaged",
    "Vehicles struggle on this broken road",

    # Water Issue
    "Water supply has stopped",
    "There is no water in my house",
    "The tap is completely dry",
    "Water pipe is leaking",
    "We have low water pressure",
    "Our area has a water shortage",
    "No drinking water is available",
    "The municipal water connection is broken",
    "Water is not reaching our homes",
    "The tap has no running water",

    # Electrical Hazard
    "Street light is not working",
    "Electricity supply is interrupted",
    "A live wire is hanging on the road",
    "There is a power outage",
    "An electric pole is damaged",
    "Sparks are coming from a wire",
    "Our neighborhood has no electricity",
    "The street lamp stopped working",
    "An electrical cable is exposed",
    "The power line is damaged",

    # Flooding
    "The street is flooded after rain",
    "Water has accumulated on the road",
    "Heavy rain caused waterlogging",
    "The road is underwater",
    "Drain water is overflowing into the street",
    "Rainwater has flooded our locality",
    "Rain has flooded the nearby street",
    "Water is covering the entire road",
    "Our neighborhood is flooded after rainfall",
    "Rainwater is collecting outside houses",

    # Waste Management
    "Garbage is not collected",
    "Dustbins are overflowing",
    "There is trash all over the street",
    "Waste has been lying here for days",
    "The garbage bin is full",
    "The area smells because of rubbish",
    "The garbage truck did not arrive",
    "Household waste is scattered everywhere",
    "The public bin has not been emptied",
    "Trash is piling up near our homes",
]

categories = (
    ["Road Damage"] * 10
    + ["Water Issue"] * 10
    + ["Electrical Hazard"] * 10
    + ["Flooding"] * 10
    + ["Waste Management"] * 10
)

# ==========================================
# 2. SPLIT DATA INTO TRAINING AND TESTING
# ==========================================

X_train, X_test, y_train, y_test = train_test_split(
    complaints,
    categories,
    test_size=0.25,
    random_state=42,
    stratify=categories
)

print("=" * 45)
print("       CIVICPULSE AI - MODEL TRAINING")
print("=" * 45)

print(f"Total complaints: {len(complaints)}")
print(f"Training complaints: {len(X_train)}")
print(f"Testing complaints: {len(X_test)}")

# ==========================================
# 3. CREATE THE MACHINE LEARNING PIPELINE
# ==========================================

model = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("classifier", LogisticRegression(max_iter=1000))
])

# ==========================================
# 4. TRAIN THE MODEL
# ==========================================

model.fit(X_train, y_train)

print("\nModel training completed successfully!")

# ==========================================
# 5. EVALUATE ON UNSEEN TEST DATA
# ==========================================

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\n" + "=" * 45)
print("             MODEL EVALUATION")
print("=" * 45)

print(f"Accuracy: {accuracy:.2%}")

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        predictions,
        labels=sorted(set(categories)),
        zero_division=0
    )
)

labels = sorted(set(categories))

matrix = confusion_matrix(
    y_test,
    predictions,
    labels=labels
)

print("Confusion Matrix")
print("Category order:", labels)
print(matrix)

# ==========================================
# 6. SAVE THE TRAINED MODEL
# ==========================================

model_path = "civicpulse_model.pkl"

joblib.dump(model, model_path)

print(f"\nModel saved successfully as: {model_path}")

# ==========================================
# 7. PREDICT A NEW CITIZEN COMPLAINT
# ==========================================

print("\n" + "=" * 45)
print("          NEW CITIZEN COMPLAINT")
print("=" * 45)

new_complaint = input("Enter a citizen complaint: ").strip()

if new_complaint:
    prediction = model.predict([new_complaint])[0]

    print("\n--- ML Prediction ---")
    print("Complaint:", new_complaint)
    print("Predicted category:", prediction)
else:
    print("No complaint entered. Prediction skipped.")

print("\nCivicPulse AI execution completed!")
