from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

#Extensions - instantiated here, bound to app in create_app()
#these are module level, so every other file can do : import app from db , without 
#importing the app object itsef (this avoids circular imports)

db = SQLAlchemy()

def create_app():
    """
    App factory : returns a fully configured flask application 
    why a factory instead of plain app = Flask(__name__)? 
    - tests can call create_app() multiple times with different configs 
    eg: one app pointing at the test DB, one at the real db 
    - blueprints and extensions are registered inside the function so, 
    there is no module level app object for other files to import and accidentally 
    create circular dependencies around
    """
    app = Flask(__name__)

    #1 configuration: 

    from config import get_config
    app.config.from_object(get_config())

    #2 extensions: 

    db.init_app(app)

    CORS(app, origins=app.config["CORS-ORIGINS"])

    #3 Blueprints: (registered after extensions so routes can use db)

    from app.api.index import index_bp # type: ignore
    from app.api.albums import albums_bp # type: ignore 
    from app.api.files import files_bp # type: ignore 
    from app.api.share import share_bp# type: ignore 
    from app.api.health import health_bp# type: ignore 

    app.register_blueprint(index_bp, url_prefix="/api")
    app.register_blueprint(albums_bp, url_prefix= "/api")
    app.register_blueprint(files_bp, url_prefix = "/api")
    app.register_blueprint(share_bp, url_prefix="/api")
    app.register_blueprint(health_bp, url_prefix = "/api")

    #Global error handlers: 
    #every response in Medvault follows the same envelope: 
    #{"succes" : bool, "data": ..., "error": null | message}

    #these error handlers make sure that's true even for unhandled exceptions 
    #404s and 405s, not just routes we write ourselves 

    @app.errorhandler(400)
    def bad_request(e): 
        return jsonify(success=False, data=None, error=str(e)), 400
    
    @app.errorhandler(404)
    def not_found(e): 
        return jsonify(success=False, data=None, error = "Resource not found"), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e): 
        return jsonify(success= False, data = None,error = "Method not allowed"), 405
    
    @app.errorhandler(500)
    def internal_error(e):
        #rollback any open transactions so that session 1 isn't left dirty 
        db.session.rollback()
        return jsonify(success=False, data = None, error = "Internal server error"),500
    
    @app.errorhandler(Exception)
    def unhandled_exception(e):
        db.session.rollback()
        app.logger.exception("Unhandled exception : %s",e)
        return jsonify(success= False, data=None, error = "An unexpected error occured"), 500
    

    #5 shell context : makes flask-shell useful for debugging 

    @app.shell_context_processor
    def make_shell_context(): 
        from app.models import(
            DICOMFile, Album, AlbumFile, 
            ShareToken, TokenAccessing, ScanError, AppSettings
        )

        return dict(
            db = db, 
            DICOMFile= DICOMFile,
            Album= Album,
            AlbumFile= AlbumFile,
            ShareToken = ShareToken,
            TokenAccessing= TokenAccessing, 
            ScanError= ScanError,
            AppSettings= AppSettings,
        )

    return app
