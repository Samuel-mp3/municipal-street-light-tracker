import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash
from blueprints.auth import login_required
from database import get_db_connection
from config import Config

prediction_bp = Blueprint('prediction', __name__)

def load_ml_model():
    if os.path.exists(Config.MODEL_FILE):
        try:
            with open(Config.MODEL_FILE, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading model pickle: {e}")
    return None

@prediction_bp.route('/prediction', methods=['GET', 'POST'])
@login_required
def predict():
    model_bundle = load_ml_model()
    
    conn = get_db_connection()
    pending_complaints = conn.execute("""
        SELECT * FROM complaints WHERE status IN ('Pending', 'In Progress') ORDER BY reported_date DESC
    """).fetchall()
    conn.close()
    
    result = None
    form_data = {}
    
    if request.method == 'POST':
        ward = request.form.get('ward', 'Ward 1').strip()
        fault_type = request.form.get('fault_type', 'Bulb Replacement').strip()
        reported_date_str = request.form.get('reported_date', datetime.now().strftime('%Y-%m-%d')).strip()
        pole_id = request.form.get('pole_id', 'POL-101').strip()
        
        form_data = {
            'ward': ward,
            'fault_type': fault_type,
            'reported_date': reported_date_str,
            'pole_id': pole_id
        }
        
        if not model_bundle:
            flash("ML Model model.pkl is not loaded. Please train the model.", "danger")
        else:
            try:
                clf = model_bundle['model']
                le_ward = model_bundle['le_ward']
                le_fault = model_bundle['le_fault']
                pole_counts = model_bundle.get('pole_counts', {})
                
                # Parse month and day of week
                try:
                    dt = datetime.strptime(reported_date_str, '%Y-%m-%d')
                    reported_month = dt.month
                    reported_dayofweek = dt.weekday()
                except ValueError:
                    reported_month = datetime.now().month
                    reported_dayofweek = datetime.now().weekday()
                    
                # Historical repeat count for pole
                historical_pole_complaints = pole_counts.get(pole_id, 1)
                
                # Encode ward (fallback to default index if unseen)
                if ward in le_ward.classes_:
                    ward_encoded = le_ward.transform([ward])[0]
                else:
                    ward_encoded = 0
                    
                # Encode fault_type (fallback to default index if unseen)
                if fault_type in le_fault.classes_:
                    fault_type_encoded = le_fault.transform([fault_type])[0]
                else:
                    fault_type_encoded = 0
                    
                # Feature DataFrame matching training columns
                feature_cols = model_bundle.get('feature_cols', ['ward_encoded', 'fault_type_encoded', 'reported_month', 'reported_dayofweek', 'historical_pole_complaints'])
                X_sample = pd.DataFrame([[ward_encoded, fault_type_encoded, reported_month, reported_dayofweek, historical_pole_complaints]], columns=feature_cols)
                
                prediction_class = clf.predict(X_sample)[0]
                probabilities = clf.predict_proba(X_sample)[0]
                confidence = float(np.max(probabilities) * 100)
                
                # Threshold for low confidence warning (65%)
                is_low_confidence = (confidence < 65.0)
                
                result = {
                    'need_attention': bool(prediction_class == 1),
                    'label': "YES - Needs Immediate Attention" if prediction_class == 1 else "NO - Standard Repair Priority",
                    'confidence': round(confidence, 1),
                    'is_low_confidence': is_low_confidence,
                    'low_confidence_message': "Prediction confidence is low. Manual verification recommended." if is_low_confidence else None,
                    'probability_yes': round(probabilities[1] * 100, 1) if len(probabilities) > 1 else 0.0,
                    'probability_no': round(probabilities[0] * 100, 1) if len(probabilities) > 0 else 0.0,
                    'historical_pole_complaints': historical_pole_complaints
                }
            except Exception as e:
                flash(f"Error making prediction: {str(e)}", "danger")
                
    accuracy = round(model_bundle['accuracy'] * 100, 1) if model_bundle and 'accuracy' in model_bundle else 85.0
    wards = model_bundle['wards'] if model_bundle and 'wards' in model_bundle else [f'Ward {i}' for i in range(1, 11)]
    fault_types = model_bundle['fault_types'] if model_bundle and 'fault_types' in model_bundle else [
        'Bulb Replacement', 'Wiring Damage', 'Transformer Failure', 'Pole Structural Damage', 'Switch Failure', 'Power Surge'
    ]
    
    return render_template(
        'prediction.html',
        result=result,
        form_data=form_data,
        pending_complaints=pending_complaints,
        accuracy=accuracy,
        wards=wards,
        fault_types=fault_types,
        today_str=datetime.now().strftime('%Y-%m-%d')
    )

@prediction_bp.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    data = request.get_json() or {}
    model_bundle = load_ml_model()
    
    if not model_bundle:
        return jsonify({'error': 'Model not available'}), 500
        
    ward = data.get('ward', 'Ward 1')
    fault_type = data.get('fault_type', 'Bulb Replacement')
    reported_date_str = data.get('reported_date', datetime.now().strftime('%Y-%m-%d'))
    pole_id = data.get('pole_id', 'POL-101')
    
    clf = model_bundle['model']
    le_ward = model_bundle['le_ward']
    le_fault = model_bundle['le_fault']
    pole_counts = model_bundle.get('pole_counts', {})
    
    try:
        dt = datetime.strptime(reported_date_str, '%Y-%m-%d')
        reported_month = dt.month
        reported_dayofweek = dt.weekday()
    except ValueError:
        reported_month = datetime.now().month
        reported_dayofweek = datetime.now().weekday()
        
    historical_pole_complaints = pole_counts.get(pole_id, 1)
    
    ward_encoded = le_ward.transform([ward])[0] if ward in le_ward.classes_ else 0
    fault_type_encoded = le_fault.transform([fault_type])[0] if fault_type in le_fault.classes_ else 0
    
    feature_cols = model_bundle.get('feature_cols', ['ward_encoded', 'fault_type_encoded', 'reported_month', 'reported_dayofweek', 'historical_pole_complaints'])
    X_sample = pd.DataFrame([[ward_encoded, fault_type_encoded, reported_month, reported_dayofweek, historical_pole_complaints]], columns=feature_cols)
    
    prediction_class = clf.predict(X_sample)[0]
    probabilities = clf.predict_proba(X_sample)[0]
    confidence = float(np.max(probabilities) * 100)
    is_low_confidence = (confidence < 65.0)
    
    return jsonify({
        'need_attention': int(prediction_class),
        'label': "YES - Immediate Attention" if prediction_class == 1 else "NO - Standard Priority",
        'confidence': round(confidence, 1),
        'is_low_confidence': is_low_confidence,
        'message': "Prediction confidence is low. Manual verification recommended." if is_low_confidence else "High confidence prediction."
    })
