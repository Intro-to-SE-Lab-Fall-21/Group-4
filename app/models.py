
from app import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(30))
    first_name = db.Column(db.String(40))
    last_name = db.Column(db.String(40))

    def check_password(self, password):
        if self.password == password:
            return True
        else:
            return False
