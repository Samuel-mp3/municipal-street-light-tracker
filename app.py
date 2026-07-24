import os
from flask import Flask, render_template
from config import Config
from database import init_db
from train_model import train_and_save_model

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize SQLite DB and seed initial data if empty
    with app.app_context():
        init_db()
        # Train ML model if model.pkl does not exist
        if not os.path.exists(Config.MODEL_FILE):
            print("Model pickle not found. Training Machine Learning model...")
            train_and_save_model()
            
    # Register Blueprints
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.complaints import complaints_bp
    from blueprints.prediction import prediction_bp
    from blueprints.reports import reports_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(reports_bp)
    
    @app.context_processor
    def inject_globals():
        return dict(current_year=2026)
        
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
        
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('500.html'), 500
        
    return app

app = create_app()

if __name__ == '__main__':
    print("Starting Municipal Street Light Fault Register & Repair Tracker on http://127.0.0.1:5000")
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
