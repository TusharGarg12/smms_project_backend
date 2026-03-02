import firebase_admin
from firebase_admin import credentials, firestore

# 1. Initialize Firebase
cred = credentials.Certificate("local-firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. Translate the IIITA Menu into AI Math (0 = Monday, 6 = Sunday)
weekly_menu = {
    "0": { # MONDAY
        "Breakfast": {"Menu_Score": 1.2, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Samosa
        "Lunch": {"Menu_Score": 1.0, "Is_Veg_Special": 0, "Is_NonVeg": 0},     # Kadhi Pakode
        "Dinner": {"Menu_Score": 1.5, "Is_Veg_Special": 1, "Is_NonVeg": 1}     # Egg Curry / Kadhai Paneer
    },
    "1": { # TUESDAY
        "Breakfast": {"Menu_Score": 0.9, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Uttapam
        "Lunch": {"Menu_Score": 0.7, "Is_Veg_Special": 0, "Is_NonVeg": 0},     # Baingan Bharta
        "Dinner": {"Menu_Score": 1.0, "Is_Veg_Special": 0, "Is_NonVeg": 0}     # Veg Kofta
    },
    "2": { # WEDNESDAY
        "Breakfast": {"Menu_Score": 1.3, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Pav Bhaji
        "Lunch": {"Menu_Score": 0.8, "Is_Veg_Special": 0, "Is_NonVeg": 0},     # Kaddu Sabzi
        "Dinner": {"Menu_Score": 1.1, "Is_Veg_Special": 0, "Is_NonVeg": 0}     # Chana Masala
    },
    "3": { # THURSDAY
        "Breakfast": {"Menu_Score": 1.0, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Medu Vada
        "Lunch": {"Menu_Score": 1.3, "Is_Veg_Special": 1, "Is_NonVeg": 0},     # Dal Makhni / Pulao
        "Dinner": {"Menu_Score": 1.2, "Is_Veg_Special": 0, "Is_NonVeg": 0}     # Rajma
    },
    "4": { # FRIDAY
        "Breakfast": {"Menu_Score": 1.4, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Poha & Jalebi
        "Lunch": {"Menu_Score": 1.0, "Is_Veg_Special": 0, "Is_NonVeg": 0},     # Aloo Bhujiya
        "Dinner": {"Menu_Score": 1.8, "Is_Veg_Special": 1, "Is_NonVeg": 1}     # Chicken / Paneer Paratha
    },
    "5": { # SATURDAY
        "Breakfast": {"Menu_Score": 1.3, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Masala Dosa
        "Lunch": {"Menu_Score": 1.6, "Is_Veg_Special": 1, "Is_NonVeg": 0},     # Chole Bhature
        "Dinner": {"Menu_Score": 0.9, "Is_Veg_Special": 0, "Is_NonVeg": 0}     # Mix Veg
    },
    "6": { # SUNDAY
        "Breakfast": {"Menu_Score": 1.4, "Is_Veg_Special": 0, "Is_NonVeg": 0}, # Aloo Paratha
        "Lunch": {"Menu_Score": 1.2, "Is_Veg_Special": 0, "Is_NonVeg": 0},     # Veg Biriyani
        "Dinner": {"Menu_Score": 1.4, "Is_Veg_Special": 0, "Is_NonVeg": 0}     # Pasta / Chowmein
    }
}

print("Uploading IIITA Mess Menu to Firebase...")

# 3. Push to Firebase Collection 'weekly_menu'
for day_idx, meals in weekly_menu.items():
    db.collection('weekly_menu').document(day_idx).set(meals)
    print(f"Uploaded Day {day_idx} successfully.")

print("✅ Complete! Your AI now has a brain for the food schedule.")