from os import error
from flask import render_template, request, flash, redirect, url_for, Blueprint, current_app
from app.forms import ForwardReplyForm, LoginForm, SignupForm, ComposeForm
from smtplib import SMTP_SSL, SMTPAuthenticationError
from app import  db
from .models import User
from flask_login import current_user, login_user, logout_user, login_required
from imap_tools import MailBox, AND
from flask_mail import Message, Mail
from mimetypes import guess_type
import sys
from bs4 import BeautifulSoup

view = Blueprint('view', __name__)
class userEmail():
    def __init__(self, uid, subject, body, sender, isHTML):
        self.uid = uid
        self.subject = subject
        self.body = body
        self.sender = sender
        self.isHTML = isHTML

emails = []
subjects = []
uids = []

def getEmails():
    user = current_user.email
    pwd = current_user.password
    with MailBox('imap.gmail.com').login(user, pwd, 'INBOX') as mailbox:
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
            emails.append(email)


@view.route('/', methods=['GET', 'POST'])
@view.route('/index/<refresh>', methods=['GET', 'POST'])
@login_required
def index(refresh="False"):
    search1 = ""
    if request.method == 'POST':
        search1 = request.form.get('search')
        if search1:
            return redirect(url_for('searchResults', search=search1))
        else:
            return redirect(url_for('index'))

    if not emails or refresh == "True":
        emails.clear()
        subjects.clear()
        uids.clear()
        getEmails()
        for email in emails:

            subjects.append(email.subject)
            uids.append(email.uid)

    #if request.method == 'POST':
    #    search1 = request.form.get('search')
    #   return redirect(url_for('searchResults', search=search1))  

    return render_template('index.html', search = 0, user = current_user.first_name, subjects = subjects, uids = uids, length1 = len(subjects))


@view.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('view.index'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid email or password')
            return redirect(url_for('view.login'))
        server = SMTP_SSL('smtp.gmail.com', 465)
        try:
            login_user(user)
            server.login(user.email, user.password)
            current_app.config['MAIL_USERNAME'] = current_user.email
            current_app.config['MAIL_PASSWORD'] = current_user.password
            current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
            flash('Success! You logged into your email!', category='success')
            return redirect(url_for('view.index'))
        except SMTPAuthenticationError:
            flash('Error, these credentials are not valid.', category ='error')
            return redirect(url_for('view.login'))
    return render_template('login.html', form=form)


@view.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    form = SignupForm()

    if form.validate_on_submit():
        email = form.email.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        password1 = form.password1.data
        password2 = form.password2.data
        server = SMTP_SSL('smtp.gmail.com', 465)

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Error! This email already has an account', category='error')
        elif password1 != password2:
            flash('Error! Passwords do not match', category='error')
        else:
            try:
                server.login(email, password1)
                new_user = User(email=email, password=password1, first_name=first_name, last_name=last_name)
                db.session.add(new_user)
                db.session.commit()
                flash('Success! You logged into your email!', category='success')
            except SMTPAuthenticationError:
                flash('Error, these credentials are not valid.', category ='error')
    return render_template("signup.html", form=form)


@view.route('/viewEmail/<uid>', methods=['GET', 'POST'])
@login_required
def viewEmail(uid):
    forward = False
    reply_flag = False
    form = ForwardReplyForm()
    current_app.config['MAIL_USERNAME'] = current_user.email
    current_app.config['MAIL_PASSWORD'] = current_user.password
    current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
    mail = Mail(current_app)

    email = userEmail('', '', '', '', '')
    for user_email in emails:
        x = int(user_email.uid)
        y = int(uid)
        if x == y:
            email = userEmail(user_email.uid, user_email.subject, user_email.body, user_email.sender, user_email.isHTML)
            if form.is_submitted():
                if form.forward.data:
                    forward = True
                    reply_flag = False
                    form.compose.body.data = email.body
                    form.compose.subject.data = 'FW: (' + email.sender + ') ' + email.subject
                    return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
                elif form.reply.data:
                    reply_flag = True
                    forward = False
                    form.compose.subject.data = email.subject
                    form.compose.email_to.data = email.sender
                    return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
                elif form.compose.validate_on_submit():
                    msg = Message()
                    recipients_string = form.compose.email_to.data
                    recipients_string = recipients_string.replace(" ", "")
                    msg.recipients = recipients_string.split(",")
                    msg.html = form.compose.body.data
                    msg.subject = form.compose.subject.data
                    msg.sender = current_app.config['MAIL_USERNAME']
                    if reply_flag:
                        msg.reply_to = email.sender
                    print(msg.extra_headers)
                    if form.compose.attachment.data.filename:
                        type = guess_type(form.compose.attachment.data.filename)
                        msg.attach(form.compose.attachment.data.filename, str(type), form.compose.attachment.data.read())
                        
                    try:
                        mail.send(msg)
                        flash('Success! Your email has been sent.', category='success')
                        return redirect(url_for('view.index'))
                    except:
                        flash('An unexpected error occured. Please try again', category='error')
                        print('Whew!', sys.exc_info()[0], 'occurred.')

            return render_template('viewEmail.html', form=form, isHTML = email.isHTML, body = email.body, sender = email.sender, receiver = current_user.email, subject = email.subject, uid = email.uid, forward=forward, reply_flag=reply_flag)
    return redirect(url_for('view.login'))


@view.route('/compose', methods=['GET', 'POST'])
@login_required
def compose():
    form = ComposeForm()
    current_app.config['MAIL_USERNAME'] = current_user.email
    current_app.config['MAIL_PASSWORD'] = current_user.password
    current_app.config['MAIL_DEFAULT_SENDER'] = current_user.email
    mail = Mail(current_app)

    if form.validate_on_submit():
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
            flash('Success! Your email has been sent.', category='success')
            return redirect(url_for('view.index'))
        except:
            flash('An unexpected error occured. Please try again', category='error')
            print('Whew!', sys.exc_info()[0], 'occurred.')
    return render_template('compose.html', form=form)

@app.route('/searchResults/<search>', methods=['GET', 'POST'])
@login_required
def searchResults(search):
    search1 = ""
    searchResultsSubjs = []
    searchResultsUids = []
    for email in emails:
        subj = email.subject.lower()
        search = search.lower()
        if search in subj:
            searchResultsSubjs.append(email.subject)
            searchResultsUids.append(email.uid)

    if request.method == 'POST':
        search1 = request.form.get('search')
        if search1:
            return redirect(url_for('searchResults', search=search1))
        else:
            return redirect(url_for('index'))
    
    return render_template('searchResults.html', search=search, user = current_user.first_name, subjects = searchResultsSubjs, uids = searchResultsUids, length1 = len(searchResultsUids))


@view.route('/logout')
@login_required
def logout():
    emails.clear()
    subjects.clear()
    uids.clear()
    logout_user()
    return redirect(url_for('view.login'))

