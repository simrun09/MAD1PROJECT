from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config

# --- Extension Instances ---
# Create extension instances here, but do not initialize them with an app.
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """Application Factory Function"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Initialize Extensions ---
    # Now, initialize the extensions with the created app instance.
    db.init_app(app)
    migrate.init_app(app, db) # This is the line that registers the 'flask db' command
    login_manager.init_app(app)

    # --- Import and Register Blueprints ---
    # Import blueprints here, inside the factory, to avoid circular imports.
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.customer import customer_bp
    from .routes.professional import professional_bp
    from .routes.shared import shared_bp
    from .routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(professional_bp, url_prefix='/professional')
    app.register_blueprint(shared_bp, url_prefix='/shared')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    # --- Context Processing ---
    # This is also a good place to define app context, for example, creating the DB tables in a shell.
    @app.shell_context_processor
    def make_shell_context():
        # This allows you to run 'flask shell' and have these models pre-imported.
        from app import models
        return {
            'db': db,
        'Users': models.Users,
        'Customers': models.Customers,
        'ServiceProfessionals': models.ServiceProfessionals,
        'Services': models.Services,
        'ServiceRequests': models.ServiceRequests,
        'Reviews': models.Reviews
        }


    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', 
                            error_code=404, 
                            error_name="Page Not Found",
                            error_description="Sorry, the page you are looking for does not exist."), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('error.html', 
                            error_code=403, 
                            error_name="Forbidden",
                            error_description="Sorry, you do not have permission to access this page."), 403

    return app
from app import models
# --- Import Models ---
# Import models at the bottom. This is a common pattern to avoid circular import errors,
# as the routes and other parts of the app may need to import `db` from this file.
