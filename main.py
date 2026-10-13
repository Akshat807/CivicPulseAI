
print("================================")
print("       CivicPulse AI")
print("  Smart City Complaint System")
print("================================")

city = input("Enter your city name: ")
complaint = input("Enter your complaint: ")

# Convert complaint into lowercase
text = complaint.lower()

# Identify the complaint category
if any(word in text for word in ["garbage", "waste", "trash", "rubbish"]):
    category = "Garbage / Waste"

elif any(word in text for word in ["water", "leakage", "pipe", "flood"]):
    category = "Water"

elif any(word in text for word in ["electricity", "power", "street light", "electric", "wire"]):
    category = "Electricity"

else:
    category = "Other / Unknown"

# Display the result
print("\n========== RESULT ==========")
print("City:", city)
print("Complaint:", complaint)
print("Category:", category)
print("Status: Registered")
