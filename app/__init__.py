from flask import Flask
from config import Config
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate


db = SQLAlchemy()

def create_app():
    from .models import User, download_attachment
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    migrate = Migrate(app, db)
    app.jinja_env.globals.update(download_attachment=download_attachment)

    from .routes import view

    app.register_blueprint(view, url_prefix='/')

    login = LoginManager(app)
    login.login_view = 'view.login'
    login.init_app(app)
    @login.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return app

