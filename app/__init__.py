from flask import Flask
from config import Config
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from os import path

def create_database(app):
    if not path.exists('app/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')

db = SQLAlchemy()
DB_NAME = "database.db"

app = Flask(__name__)
app.config.from_object(Config)

app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['SQALCHEMY_DATABASE_URI'] = f'sqlight:///{DB_NAME}'
app.config['MAIL_SERVER'] = ''
app.config['MAIL_PORT'] = 25
app.config['SMTP_PORT'] = ''
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

from app import routes
from .models import User

db.init_app(app)
create_database(app)



