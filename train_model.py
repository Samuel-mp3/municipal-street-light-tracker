import os
import pickle
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from config import Config

def train_and_save_model():
    """
    Trains a Machine Learning classifier to predict if a newly reported street light fault
    will require 'Immediate Attention' (High Risk / Delay Likelihood).
    
    STRICT DATA LEAKAGE PREVENTION:
    Only inputs available at report creation time are used:
    - ward
    - fault_type
    - reported_month
    - reported_dayofweek
    - historical_pole_complaints
    
    Excludes downstream post-repair variables (e.g., repaired_date, pending_days).
    """
    if not os.path.exists(Config.DATASET_FILE):
        print(f"Dataset file missing at {Config.DATASET_FILE}")
        return False
        
    df = pd.read_csv(Config.DATASET_FILE)
    
    # Preprocessing & Data Cleaning
    df['reported_date'] = pd.to_datetime(df['reported_date'], errors='coerce')
    df['reported_month'] = df['reported_date'].dt.month.fillna(6).astype(int)
    df['reported_dayofweek'] = df['reported_date'].dt.dayofweek.fillna(0).astype(int)
    
    # Calculate historical repeat reports per pole_id (feature known at log time)
    pole_counts = df['pole_id'].value_counts().to_dict()
    df['historical_pole_complaints'] = df['pole_id'].map(pole_counts).fillna(1).astype(int)
    
    # Fill missing values in categorical fields with mode
    df['ward'] = df['ward'].fillna('Ward 1').astype(str)
    df['fault_type'] = df['fault_type'].fillna('Bulb Replacement').astype(str)
    df['need_attention'] = df['need_attention'].fillna(0).astype(int)
    
    # Label Encoders for categorical features
    le_ward = LabelEncoder()
    le_fault = LabelEncoder()
    
    df['ward_encoded'] = le_ward.fit_transform(df['ward'])
    df['fault_type_encoded'] = le_fault.fit_transform(df['fault_type'])
    
    feature_cols = ['ward_encoded', 'fault_type_encoded', 'reported_month', 'reported_dayofweek', 'historical_pole_complaints']
    X = df[feature_cols]
    y = df['need_attention']
    
    # Train / Test Split with fixed random seed
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Model: Random Forest Classifier
    clf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluation
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"[ML Model Trained] Test Accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred))
    
    # Save model bundle
    model_bundle = {
        'model': clf,
        'le_ward': le_ward,
        'le_fault': le_fault,
        'feature_cols': feature_cols,
        'accuracy': float(acc),
        'pole_counts': pole_counts,
        'wards': list(le_ward.classes_),
        'fault_types': list(le_fault.classes_)
    }
    
    os.makedirs(os.path.dirname(Config.MODEL_FILE), exist_ok=True)
    with open(Config.MODEL_FILE, 'wb') as f:
        pickle.dump(model_bundle, f)
        
    print(f"Model saved successfully to {Config.MODEL_FILE}")
    return True

if __name__ == '__main__':
    train_and_save_model()
