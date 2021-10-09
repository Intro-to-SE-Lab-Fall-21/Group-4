
from app import db, login
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

@login.user_loader
def load_user(id):
    return User.query.get(int(id))