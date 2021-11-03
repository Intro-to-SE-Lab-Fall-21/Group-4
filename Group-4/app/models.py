from flask import current_app, flash, redirect, url_for
from app import db
from flask_login import UserMixin, current_user, login_user
from imap_tools import MailBox, AND
from flask_mail import Message, Mail
from bs4 import BeautifulSoup
from mimetypes import guess_type
from smtplib import SMTPAuthenticationError, SMTP_SSL
import sys

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(30))
    first_name = db.Column(db.String(40))
    last_name = db.Column(db.String(40))

    # checks password to make sure they are equal
    def check_password(self, password):
        if self.password == password:
            return True
        else:
            return False

# user email class
class userEmail():
    def __init__(self, uid, subject, body, sender, isHTML):
        self.uid = uid
        self.subject = subject
        self.body = body
        self.sender = sender
        self.isHTML = isHTML

# stores lists of the user's emails
class Emails():
    def __init__(self):
        self.uids= []
        self.emails = []
        self.subjects = []

    # gets the user's emails
    def getEmails(self, user):
        email = user.email
        pwd = user.password
        with MailBox('imap.gmail.com').login(email, pwd, 'INBOX') as mailbox:
            uids = [msg.uid for msg in mailbox.fetch()]
            bodies = [msg.text for msg in mailbox.fetch()]
            bodiesHTML = [msg.html for msg in mailbox.fetch()]
            subjects = [msg.subject for msg in mailbox.fetch(AND(all=True))]
            senders = [msg.from_ for msg in mailbox.fetch()]

            uids.reverse()
            subjects.reverse()
            bodiesHTML.reverse()
            bodies.reverse()
            senders.reverse()

            for i in range(len(subjects)):
                email = userEmail(uids[i], subjects[i], bodiesHTML[i], senders[i], False) 
                soup = BeautifulSoup(email.body, 'html.parser')
                email.body = soup.decode_contents()
                if(bodiesHTML[i] == ""):
                    email.body = bodies[i]
                    email.isHTML = False

                else:
                    email.isHTML = True
                    
                self.emails.append(email)
                self.uids.append(email.uid)
                self.subjects.append(email.subject)
    
    # selects the email the user wants to display
    def selectEmail(self, uid):
        found_email = userEmail('', '', '', '', '')
        for user_email in self.emails:
            x = int(user_email.uid)
            y = int(uid)
            if x == y:
                found_email = userEmail(user_email.uid, user_email.subject, user_email.body, user_email.sender, user_email.isHTML)
                return found_email
        return 'Failed'

    # clears all emails
    def clearAll(self):
        self.emails.clear()
        self.uids.clear()
        self.subjects.clear()

# sends the emails
def send_composed_message(form):
    current_app.config['MAIL_USERNAME'] = current_user.email
    current_app.config['MAIL_PASSWORD'] = current_user.password
    current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
    mail = Mail(current_app)

    msg = Message()
    recipients_string = form.email_to.data
    recipients_string = recipients_string.replace(" ", "")
    msg.recipients = recipients_string.split(",")
    msg.html = form.body.data
    msg.subject = form.subject.data
    msg.sender = current_app.config['MAIL_USERNAME']
    
    if form.attachment.data.filename:
        type = guess_type(form.attachment.data.filename)
        msg.attach(form.attachment.data.filename, str(type), form.attachment.data.read())
    try:
        mail.send(msg)
        return True
    except:
        return False

# makes sure the user is authorized
def authorize(form):
    user = User.query.filter_by(email=form.email.data).first()
    if user is None or not user.check_password(form.password.data):
        flash('Invalid email or password')
        return redirect(url_for('view.login'))

    login_user(user)
    server = SMTP_SSL('smtp.gmail.com', 465)
    # tries to log-in user
    try:
        server.login(user.email, user.password)
        current_app.config['MAIL_USERNAME'] = current_user.email
        current_app.config['MAIL_PASSWORD'] = current_user.password
        current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
        flash('Success! You logged into your email!', category='success')
        return redirect(url_for('view.index'))

    # error if credentials are invalid
    except SMTPAuthenticationError:
        flash('Error, these credentials are not valid.', category ='error')
        return redirect(url_for('view.login'))