from app import app
from flask_mail import Mail, Message

if __name__ == '__main__':
    app.run(debug=True)