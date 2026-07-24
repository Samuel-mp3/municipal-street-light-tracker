import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'municipal_street_light_secret_key_2026_super_secure')
    DATABASE = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'data', 'street_lights.db'))
    SCHEMA_FILE = os.path.join(BASE_DIR, 'data', 'schema.sql')
    DATASET_FILE = os.path.join(BASE_DIR, 'data', 'dataset.csv')
    MODEL_FILE = os.path.join(BASE_DIR, 'data', 'model.pkl')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
