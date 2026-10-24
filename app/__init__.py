import os
from flask import Flask, render_template
from app.config import Config
from app.database import close_db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload directories exist
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'issues'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'resolutions'), exist_ok=True)

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Register Blueprints
    from app.routes import auth, public, citizen, staff, admin, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(public.bp)
    app.register_blueprint(citizen.bp)
    app.register_blueprint(staff.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(api.bp)

    # Context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            'CATEGORIES': app.config['CATEGORIES'],
            'SEVERITY_LEVELS': app.config['SEVERITY_LEVELS'],
            'STATUS_WORKFLOW': app.config['STATUS_WORKFLOW']
        }

    @app.template_filter('format_date')
    def format_date(value):
        if not value:
            return ''
        if isinstance(value, str):
            return value[:10]
        try:
            return value.strftime('%Y-%m-%d')
        except Exception:
            return str(value)[:10]

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        safe_stats = {'total': 0, 'resolved': 0, 'in_progress': 0, 'citizens': 0, 'resolution_rate': 0}
        return render_template('public/index.html', stats=safe_stats, recent_issues=[], error_msg="The requested page could not be located."), 404

    @app.errorhandler(500)
    def server_error(e):
        safe_stats = {'total': 0, 'resolved': 0, 'in_progress': 0, 'citizens': 0, 'resolution_rate': 0}
        return render_template('public/index.html', stats=safe_stats, recent_issues=[], error_msg="A municipal system error occurred. Please try again."), 500


    return app
