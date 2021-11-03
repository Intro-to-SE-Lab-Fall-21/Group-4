from app import create_app
from flask_mail import Mail, Message

app = create_app()
if __name__ == '__main__':
    app.run(debug=True)