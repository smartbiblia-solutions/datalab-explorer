from flask import Flask
from extensions import db, login_manager, bcrypt
import os
import click


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    #app.config['static_url_path'] = '/apps/brgm-publications-explorer/static' # cpanel deployment, Uncomment if needed

    # Load configuration from config.py
    app.config.from_object('config')

    # Initialize extensions with the app instance
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Configure login manager
    login_manager.login_view = 'auth.login'  # Will create this route later
    login_manager.login_message_category = 'info'

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Inject config into all templates
    @app.context_processor
    def inject_config():
        return {'config': app.config}

    # Register public blueprint first as it will handle the root URL
    from modules.public.routes import public_bp
    app.register_blueprint(public_bp)

    # Register the admin blueprint
    from modules.admin.routes import admin_bp
    app.register_blueprint(admin_bp)

    # Register the auth blueprint
    from modules.auth.routes import auth_bp
    app.register_blueprint(auth_bp)

    # Conditionally register (plug-in) modules based on config
    if app.config.get('ENABLE_PLAYGROUND_LAB'):
        from modules.playground_lab.routes import playground_lab_bp
        app.register_blueprint(playground_lab_bp)

    if app.config.get('ENABLE_PLAYGROUND_GENERIC'):
        from modules.playground_generic.routes import playground_generic_bp
        app.register_blueprint(playground_generic_bp)

    if app.config.get('ENABLE_EMBEDDING_ATLAS'):
        from modules.embedding_atlas.routes import embedding_atlas_bp
        app.register_blueprint(embedding_atlas_bp)

    # Define a CLI command to initialize the database
    @app.cli.command("init-db")
    def init_db_command():
        """Creates the database tables."""
        with app.app_context():
            # Import models here to prevent circular dependencies
            from models import User, PublishedView
            db.create_all()
        print("Initialized the database.")

    @app.cli.command("add-user")
    @click.argument("username")
    @click.argument("password")
    def add_user_command(username, password):
        """Creates a new admin user."""
        with app.app_context():
            from models import User
            from extensions import db, bcrypt
            if User.query.filter_by(username=username).first():
                print(f"User {username} already exists.")
                return
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            print(f"User {username} created successfully.")

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host='0.0.0.0')
