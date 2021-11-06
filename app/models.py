from flask import current_app, flash, redirect, url_for
from app import db
from flask_login import UserMixin, current_user, login_user
from imap_tools import MailBox, AND
from flask_mail import Message, Mail
from bs4 import BeautifulSoup
from mimetypes import guess_type
from smtplib import SMTPAuthenticationError, SMTP_SSL
from sqlalchemy.sql import func
import os
import imaplib

# User SQLAlchemy class for database management
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.String(30))
    first_name = db.Column(db.String(40))
    last_name = db.Column(db.String(40))
    notes = db.relationship('Note')

    # Function to check user password against an entered password.
    def check_password(self, password):
        if self.password == password:
            return True
        else:
            return False

# Note SQLAlchemy class for database managementx
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    data = db.Column(db.String(10000))
    date = db.Column(db.DateTime(timezone=True), default=func.now())
    deleted = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# Class to contain the email information relevant for our client.
class userEmail():
    def __init__(self, uid, subject, body, sender, isHTML, attachments):
        self.uid = uid
        self.subject = subject
        self.body = body
        self.sender = sender
        self.isHTML = isHTML
        self.attachments = attachments


# Class to hold our list of emals, uids, and subjects, as well as helper functions
# to load and clear these values, or select a singular email. 
class Emails():
    def __init__(self):
        self.uids= []
        self.emails = []
        self.subjects = []

    # Function to login to imap server and fetch all emails. Loads the lists
    # uids, emails, and subjects with all the emails.
    def getEmails(self, user, folder):
        email = user.email
        pwd = user.password
        with MailBox('imap.gmail.com').login(email, pwd, initial_folder=folder) as mailbox:
            #mailbox.delete([msg.uid for msg in mailbox.fetch() if 'willthisdelete' in msg.html])
            attachments = []
            bodies = []
            bodiesHTML = []
            subjects = []
            senders = []
            uids = []
            for msg in mailbox.fetch(reverse=True, bulk=True):
                found_att = []
                for att in msg.attachments:
                    found_att.append(att)
                attachments.append(found_att)
                bodies.append(msg.text)
                bodiesHTML.append(msg.html)
                subjects.append(msg.subject)
                senders.append(msg.from_)
                uids.append(msg.uid)
            
            for i in range(len(subjects)):
                email = userEmail(uids[i], subjects[i], bodiesHTML[i], senders[i], False, attachments[i]) 
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

    def moveToTrash(self, user, uid):
        email = user.email
        pwd = user.password
        with MailBox('imap.gmail.com').login(email, pwd) as mailbox:
            mailbox.move(uid, '[Gmail]/Trash')
    
    # Selects a particular email (based on uid) in the emails list.
    def selectEmail(self, uid):
        found_email = userEmail('', '', '', '', False, [])
        for user_email in self.emails:
            x = int(user_email.uid)
            y = int(uid)
            if x == y:
                found_email = userEmail(user_email.uid, user_email.subject, user_email.body, user_email.sender, user_email.isHTML, user_email.attachments)
                return found_email
        return 'Failed'

    # Clears the emails, uids, and subjects from their respective lists.
    def clearAll(self):
        self.emails.clear()
        self.uids.clear()
        self.subjects.clear()

# Function to send an email (takes a compose form as a parameter)
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


# Function to login a user (takes a login form as a parameter)
def authorize(form):
    user = User.query.filter_by(email=form.email.data).first()
    
    # Checks database for user, throws an error if the user does not exist
    # or the password is wrong
    if user is None or not user.check_password(form.password.data):
        flash('Invalid email or password')
        return redirect(url_for('view.login'))
    login_user(user)
    server = SMTP_SSL('smtp.gmail.com', 465)

    # Tries to login the user to the actual email server.
    try:
        server.login(user.email, user.password)
        current_app.config['MAIL_USERNAME'] = current_user.email
        current_app.config['MAIL_PASSWORD'] = current_user.password
        current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
        flash('Success! You logged into your email!', category='success')
        return redirect(url_for('view.index'))
    
    # Error if the email server rejects user's credentials.
    except SMTPAuthenticationError:
        flash('Error, these credentials are not valid.', category ='error')
        return redirect(url_for('view.login'))


# Helper function for attachments. Finds the user's downloads folder and returns the path.
def get_download_path(filename):
    """Returns the default downloads path for linux or windows"""
    if os.name == 'nt':
        import winreg
        sub_key = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders'
        downloads_guid = '{374DE290-123F-4565-9164-39C4925E467B}'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
            location = winreg.QueryValueEx(key, downloads_guid)[0]
        return location + '\\' + filename
    else:
        return os.path.join(os.path.expanduser('~'), 'downloads/' + filename)

# Function to download a particular file. Takes an attachment object 
def download_attachment(attachment):
    filename = str(attachment.filename)
    filename = filename.replace(' ', '_')
    path = get_download_path(filename)
    with open(path, 'wb') as download:
        download.write(attachment.payload)
