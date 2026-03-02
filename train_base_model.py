import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


def train_and_save_model():
    # 1. Load the specific dataset
    df = pd.read_csv("smms_complete_dataset_with_meals (2).csv")

    # 2. Select features based on the dataset and the paper's methodology
    features = [
        'Day_of_Week', 'Total_Registered', 'Exam_Pressure',
        'Is_Veg_Special', 'Is_NonVeg', 'Menu_Score',
        'Temp_Max', 'Rain_mm', 'Lag_1_Dinner', 'Lag_7_Dinner', 'Rolling_Avg_3Day'
    ]
    target = 'Target_Dinner'

    # Fill any missing values for safety
    df = df.fillna(0)

    X = df[features]
    y = df[target]

    # 3. Split data (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    # 4. Create LightGBM datasets
    train_data = lgb.Dataset(X_train, label=y_train)
    test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

    # 5. Define parameters for the causal model
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'learning_rate': 0.05,
        'num_leaves': 31,
        'verbose': -1
    }

    # 6. Train the initial base model
    print("Training base model in PyCharm...")
    model = lgb.train(
        params,
        train_data,
        num_boost_round=200,
        valid_sets=[test_data],
        callbacks=[lgb.early_stopping(stopping_rounds=20)]
    )

    # 7. Evaluate
    preds = model.predict(X_test)

    # FIXED: Calculate MSE first, then take the square root using numpy
    mse = mean_squared_error(y_test, preds)
    rmse = np.sqrt(mse)

    print(f"Base Model RMSE: {rmse:.2f} students")

    # 8. Save the model to project folder
    model.save_model("smms_lightgbm_model.txt")
    print("Model saved successfully as 'smms_lightgbm_model.txt'.")


if __name__ == "__main__":
    train_and_save_model()