import pandas as pd
import numpy as np
import lightgbm as lgb
from flask import Flask, jsonify
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import requests
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

# --- FIREBASE SETUP ---
cred = credentials.Certificate("local-firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

MODEL_PATH = "smms_lightgbm_model.txt"


# ---------------------------------------------------------
# NEW AUTOMATION & WEATHER MODULE
# ---------------------------------------------------------

def get_average_weather():
    """
    Fetches the average temperature and total rainfall for the last 3 hours
    for the IIIT Allahabad campus (Prayagraj).
    """
    try:
        # Prayagraj exact coordinates
        lat, lon = 25.4358, 81.8463
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,rain&timezone=Asia%2FKolkata&past_days=1"

        response = requests.get(url).json()

        # Get current time and round down to the nearest hour
        now = datetime.datetime.now()
        current_hour_str = now.strftime("%Y-%m-%dT%H:00")

        times = response['hourly']['time']
        temps = response['hourly']['temperature_2m']
        rains = response['hourly']['rain']

        if current_hour_str in times:
            current_idx = times.index(current_hour_str)
            # Slice the last 3 hours (prevent negative index if it just started)
            start_idx = max(0, current_idx - 3)
            past_3_temps = temps[start_idx: current_idx + 1]
            past_3_rains = rains[start_idx: current_idx + 1]

            avg_temp = round(sum(past_3_temps) / len(past_3_temps), 2)
            total_rain = round(sum(past_3_rains), 2)

            return avg_temp, total_rain
    except Exception as e:
        print(f"Weather API Error: {e}")

    # Fallback default if internet fails
    return 30.0, 0.0


def get_dynamic_features(meal_type, is_tomorrow=False):
    """
    Fetches real-time context.
    Now automatically queries Firebase for the exact Menu Score!
    """
    now = datetime.datetime.now()

    # If we are predicting for tomorrow, add 1 day to the calendar
    target_date = now + datetime.timedelta(days=1) if is_tomorrow else now
    weekday_idx = str(target_date.weekday())  # "0" (Monday) to "6" (Sunday)

    # 1. Fetch live weather
    avg_temp, total_rain = get_average_weather()

    # 2. Fetch live Menu Data from Firebase
    menu_score = 1.0
    is_veg = 0
    is_nonveg = 0

    try:
        menu_ref = db.collection('weekly_menu').document(weekday_idx).get()
        if menu_ref.exists:
            # Look inside the document for "Breakfast", "Lunch", or "Dinner"
            menu_data = menu_ref.to_dict().get(meal_type, {})
            menu_score = menu_data.get('Menu_Score', 1.0)
            is_veg = menu_data.get('Is_Veg_Special', 0)
            is_nonveg = menu_data.get('Is_NonVeg', 0)
            print(f"[{meal_type}] Loaded Menu Score: {menu_score} | Veg: {is_veg} | NonVeg: {is_nonveg}")
    except Exception as e:
        print(f"Error fetching menu from Firebase: {e}")

    return pd.DataFrame([{
        'Day_of_Week': target_date.weekday(),
        'Total_Registered': 575,
        'Exam_Pressure': 0.0,  # We will make this dynamic next!
        'Is_Veg_Special': is_veg,
        'Is_NonVeg': is_nonveg,
        'Menu_Score': menu_score,
        'Temp_Max': avg_temp,
        'Rain_mm': total_rain,
        'Lag_1_Dinner': 450.0,
        'Lag_7_Dinner': 460.0,
        'Rolling_Avg_3Day': 455.0
    }])


def automated_learning_pipeline(meal_type):
    """
    The automated brain. This runs on a schedule, fetches real data,
    trains the model, and updates Firebase for the next meal automatically.
    """
    print(f"\n--- ⏰ WAKING UP: Processing {meal_type} Data ---")
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    avg_temp, total_rain = get_average_weather()
    print(f"Live Weather Context -> Temp: {avg_temp}°C | Rain: {total_rain}mm")

    try:
        # 1. Fetch real attendance scans from Firebase
        entries_ref = db.collection('attendance').document(today_str).collection('entries').get()
        real_headcount = len(entries_ref)
        print(f"Total students scanned for {meal_type}: {real_headcount}")

        if real_headcount > 0:
            # 2. Train the model with today's live data
            X_today = get_dynamic_features(meal_type, is_tomorrow=False)
            y_today = np.array([real_headcount])
            lgb_train_new = lgb.Dataset(X_today, label=y_today)

            print("Initiating Continuous Learning...")
            updated_model = lgb.train(
                params={'objective': 'regression', 'learning_rate': 0.01},
                train_set=lgb_train_new,
                num_boost_round=1,
                init_model=MODEL_PATH,
                keep_training_booster=True
            )
            updated_model.save_model(MODEL_PATH)
            print("Model successfully updated its weights!")

            # 3. Predict the next meal's crowd and update Flutter automatically!
            model = lgb.Booster(model_file=MODEL_PATH)
            X_tomorrow = get_dynamic_features(meal_type, is_tomorrow=True)
            predicted_crowd = model.predict(X_tomorrow)[0]

            db.collection('mess_data').document('prediction').set({
                'expected_students': int(predicted_crowd),
                'timestamp': firestore.SERVER_TIMESTAMP
            }, merge=True)
            print(f"SUCCESS: Pushed next prediction ({int(predicted_crowd)}) to Firebase Dashboard.")

        else:
            print("No scans found in Firebase. Skipping training.")

    except Exception as e:
        print(f"Automation Error: {e}")


# ---------------------------------------------------------
# SET UP THE SERVER ALARM CLOCK (CRON JOBS)
# ---------------------------------------------------------
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
# Breakfast ends at 11:00 AM
scheduler.add_job(func=automated_learning_pipeline, trigger="cron", args=['Breakfast'], hour=11, minute=0)
# Lunch ends at 4:00 PM (16:00)
scheduler.add_job(func=automated_learning_pipeline, trigger="cron", args=['Lunch'], hour=16, minute=0)
# Dinner ends at 11:00 PM (23:00)
scheduler.add_job(func=automated_learning_pipeline, trigger="cron", args=['Dinner'], hour=23, minute=0)

scheduler.start()
print("⏰ Cron Scheduler Started. Waiting for next meal time...")


# ---------------------------------------------------------
# FLASK API ROUTES (For manual triggers from the app)
# ---------------------------------------------------------

@app.route('/train_incremental', methods=['POST'])
def train_incremental():
    """Manual trigger for continuous learning via the app"""
    # ... logic handled by automation now, keeping endpoint for manual override
    automated_learning_pipeline("Manual App Trigger")
    return jsonify({"status": "success", "message": "Manual training triggered successfully."})


@app.route('/predict', methods=['GET'])
def predict():
    """Manual trigger to update the prediction via the app"""
    try:
        model = lgb.Booster(model_file=MODEL_PATH)

        # 1. SMART LOGIC: Decide the next meal based on current time
        current_hour = datetime.datetime.now().hour

        if current_hour < 11:
            next_meal = "Lunch"
            is_tom = False
        elif current_hour < 16:
            next_meal = "Dinner"
            is_tom = False
        else:
            # If it's after 4 PM, the next meal is Breakfast tomorrow
            next_meal = "Breakfast"
            is_tom = True

        # 2. Fetch the correct dynamic features
        X_next_meal = get_dynamic_features(next_meal, is_tomorrow=is_tom)
        predicted_crowd = model.predict(X_next_meal)[0]

        # 3. Update Firebase (saving the meal name too!)
        db.collection('mess_data').document('prediction').set({
            'expected_students': int(predicted_crowd),
            'meal_name': next_meal,  # Flutter can use this later!
            'timestamp': firestore.SERVER_TIMESTAMP
        }, merge=True)

        return jsonify({"status": "success", "predicted": int(predicted_crowd), "meal": next_meal})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # use_reloader=False prevents the scheduler from running twice when debugging
    app.run(host='0.0.0.0', debug=True, port=5000, use_reloader=False)