
from flask import Flask
from config import Config
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_migrate import Migrate
from os import path


'''def create_database(app):
    if not path.exists('app/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')'''


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'


app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
app.config['MAIL_SERVER'] = ''
app.config['MAIL_PORT'] = 25
app.config['SMTP_PORT'] = ''
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False

from app import models, routes

#db.init_app(app)
#create_database(app)



