import os 
from dotenv import load_dotenv
load_dotenv()

class Config: 
    #flask core 
    SECRET_KEY: str = os.getenv("SECRET KEY", "change-me-in-production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TESTING: bool = False

    #DATABASE 
    SQLALCHEMY_DATABAS_URI : str = os.getenv(
        "DATABASE_URL", 
        "sqlite://medvault.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping" : True, 
    }

    #CORS 

    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")

    #DICOM FILE STORAGE 
    DICOM_STORAGE_PATH: str = os.getenv("DICOM_STORAGE_PATH", "../sample_data")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", 512))

    #ML MODELS 
    ML_MODELS_PATH: str = os.getenv("ML_MODELS_PATH", "./app/ml/models")

    #sharing 
    DEFAULT_TOKEN_EXPIRY_DAYS: int = int(os.getenv("DEFAULT_TOKEN_EXPIRY_DAYS", 7))

class DevelopmentConfig(Config):
    DEBUG: bool = True

class TestingConfig(Config): 
    TESTING: bool = True
    SQLALCHEMY_DATABAS_URI: str = "sqlite:///:memory:"
    #in memory sqlite for tests, created fresh and destroyed after each run 
    #no test file left on disk, no cross test pollution 

class ProductionConfig(Config):
    DEBUG: bool = False 

_config_map: dict = {
    "development" : DevelopmentConfig,
    "testing" : TestingConfig,
    "production" : ProductionConfig
}

def get_config()-> Config:
    env = os.getenv("FLASK_ENV", "development")
    return _config_map.get(env, DevelopmentConfig)
